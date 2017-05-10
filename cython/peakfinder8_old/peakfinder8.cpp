//
//  peakfinder8.cpp
//
//  Created by Anton Barty on 15/2/17.
//  Copyright © 2017 Anton Barty. All rights reserved.
//
//  Splits out peakfinder8 into a separate routine to make it more portable.
//
//  This routine is mainly plain C (as are most Cheetah bottom-level routines)
//  and as with the rest of Cheetah is distributed as open source
//  under the Gnu Public License v3 or later.
//
//  Feel free to copy this .cpp file into your own code.
//  If you do so, please give credit to Cheetah using the citation from here:
//  http://www.desy.de/~barty/cheetah/Cheetah/Welcome.html
//



#include <stdio.h>
#include <string.h>
#include <math.h>
#include <stdlib.h>

#include "peakfinders.h"



/*
 *
 *	Cheetah Peakfinder8
 *  Count peaks by searching for connected pixels above threshold
 *	Includes modifications during Cherezov December 2014 LE80
 *	Anton Barty
 */
int peakfinder8(tPeakList *peaklist, float *data, char *mask, float *pix_r, long asic_nx, long asic_ny, long nasics_x, long nasics_y, float ADCthresh,
                float hitfinderMinSNR, long hitfinderMinPixCount, long hitfinderMaxPixCount, long hitfinderLocalBGRadius)
{

    // Derived values
    long pix_nx = asic_nx * nasics_x;
    long pix_ny = asic_ny * nasics_y;
    long pix_nn = pix_nx * pix_ny;
    //long	asic_nn = asic_nx*asic_ny;
    long hitfinderNpeaksMax = peaklist->nPeaks_max;

    peaklist->nPeaks = 0;
    peaklist->peakNpix = 0;
    peaklist->peakTotal = 0;

    // Variables for this hitfinder
    long nat = 0;
    long lastnat = 0;
    //long	counter=0;
    float total;
    int search_x[] = { 0, -1, 0, 1, -1, 1, -1, 0, 1 };
    int search_y[] = { 0, -1, -1, -1, 0, 0, 1, 1, 1 };
    int search_n = 9;
    long e;
    long *inx = (long *) calloc(pix_nn, sizeof(long));
    long *iny = (long *) calloc(pix_nn, sizeof(long));
    float thisI, thisIraw;
    float totI, totIraw;
    float maxI, maxIraw;
    float snr;
    float peak_com_x;
    float peak_com_y;
    long thisx;
    long thisy;
    long fs, ss;
    float com_x, com_y, com_e;
    float thisADCthresh;

    nat = 0;
    //counter = 0;
    total = 0.0;
    snr = 0;
    maxI = 0;

    /*
     *	Create a buffer for image data so we don't nuke the main image by mistake
     */
    float *temp = (float*) calloc(pix_nn, sizeof(float));
    memcpy(temp, data, pix_nn * sizeof(float));

    /*
     *	Apply mask (multiply data by 0 to ignore regions - this makes data below threshold for peak finding)
     */
    for (long i = 0; i < pix_nn; i++) {
        temp[i] *= mask[i];
    }

    /*
     *	Determine noise and offset as a funciton of radius
     */
    float fminr, fmaxr;
    long lminr, lmaxr;
    fminr = 1e9;
    fmaxr = -1e9;

    // Figure out radius bounds
    for (long i = 0; i < pix_nn; i++) {
        if (pix_r[i] > fmaxr)
            fmaxr = pix_r[i];
        if (pix_r[i] < fminr)
            fminr = pix_r[i];
    }
    lmaxr = (int) ceil(fmaxr) + 1;
    lminr = 0;

    // Allocate and zero arrays
    float *rsigma = (float*) calloc(lmaxr, sizeof(float));
    float *roffset = (float*) calloc(lmaxr, sizeof(float));
    long *rcount = (long*) calloc(lmaxr, sizeof(long));
    float *rthreshold = (float*) calloc(lmaxr, sizeof(float));

    long *peakpixels = (long *) calloc(hitfinderMaxPixCount, sizeof(long));
    char *peakpixel = (char *) calloc(pix_nn, sizeof(char));

    for (long i = 0; i < lmaxr; i++) {
        rthreshold[i] = 1e9;
    }

    // Compute sigma and average of data values at each radius
    // From this, compute the ADC threshold to be applied at each radius
    // Iterate a few times to reduce the effect of positive outliers (ie: peaks)
    long thisr;
    float thisoffset, thissigma;
    for (long counter = 0; counter < 5; counter++) {
        for (long i = 0; i < lmaxr; i++) {
            roffset[i] = 0;
            rsigma[i] = 0;
            rcount[i] = 0;
        }
        for (long i = 0; i < pix_nn; i++) {
            if (mask[i] != 0) {
                thisr = lrint(pix_r[i]);
                if (temp[i] < rthreshold[thisr]) {
                    roffset[thisr] += temp[i];
                    rsigma[thisr] += (temp[i] * temp[i]);
                    rcount[thisr] += 1;
                }
            }
        }
        for (long i = 0; i < lmaxr; i++) {
            if (rcount[i] == 0) {
                roffset[i] = 0;
                rsigma[i] = 0;
                rthreshold[i] = 1e9;
                //rthreshold[i] = ADCthresh;		// For testing
            }
            else {
                thisoffset = roffset[i] / rcount[i];
                thissigma = sqrt(rsigma[i] / rcount[i] - ((roffset[i] / rcount[i]) * (roffset[i] / rcount[i])));
                roffset[i] = thisoffset;
                rsigma[i] = thissigma;
                rthreshold[i] = roffset[i] + hitfinderMinSNR * rsigma[i];
                if (rthreshold[i] < ADCthresh)
                    rthreshold[i] = ADCthresh;
                //rthreshold[i] = ADCthresh;		// For testing
            }
        }
    }


    com_x = 0;
    com_y = 0;

    // Loop over modules (8x8 array)
    //counter = 0;
    long peakCounter = 0;
    for (long mj = 0; mj < nasics_y; mj++) {
        for (long mi = 0; mi < nasics_x; mi++) {

            // Loop over pixels within a module
            for (long j = 1; j < asic_ny - 1; j++) {
                for (long i = 1; i < asic_nx - 1; i++) {

                    ss = (j + mj * asic_ny) * pix_nx;
                    fs = i + mi * asic_nx;
                    e = ss + fs;

                    if (e > pix_nn) {
                        printf("Array bounds error: e=%li\n", e);
                        exit(1);
                    }

                    thisr = lrint(pix_r[e]);
                    thisADCthresh = rthreshold[thisr];

                    if (temp[e] > thisADCthresh && peakpixel[e] == 0) {
                        // This might be the start of a new peak - start searching
                        inx[0] = i;
                        iny[0] = j;
                        peakpixels[0] = e;
                        nat = 1;
                        totI = 0;
                        totIraw = 0;
                        maxI = 0;
                        maxIraw = 0;
                        peak_com_x = 0;
                        peak_com_y = 0;

                        // Keep looping until the pixel count within this peak does not change
                        do {

                            lastnat = nat;
                            // Loop through points known to be within this peak
                            for (long p = 0; p < nat; p++) {
                                // Loop through search pattern
                                for (long k = 0; k < search_n; k++) {
                                    // Array bounds check
                                    if ((inx[p] + search_x[k]) < 0)
                                        continue;
                                    if ((inx[p] + search_x[k]) >= asic_nx)
                                        continue;
                                    if ((iny[p] + search_y[k]) < 0)
                                        continue;
                                    if ((iny[p] + search_y[k]) >= asic_ny)
                                        continue;

                                    // Neighbour point in big array
                                    thisx = inx[p] + search_x[k] + mi * asic_nx;
                                    thisy = iny[p] + search_y[k] + mj * asic_ny;
                                    e = thisx + thisy * pix_nx;

                                    //if(e < 0 || e >= pix_nn){
                                    //	printf("Array bounds error: e=%i\n",e);
                                    //	continue;
                                    //}

                                    thisr = lrint(pix_r[e]);
                                    thisADCthresh = rthreshold[thisr];

                                    // Above threshold?
                                    if (temp[e] > thisADCthresh && peakpixel[e] == 0 && mask[e] != 0) {
                                        //if(nat < 0 || nat >= global->pix_nn) {
                                        //	printf("Array bounds error: nat=%i\n",nat);
                                        //	break
                                        //}
                                        thisI = temp[e] - roffset[thisr];
                                        totI += thisI; // add to integrated intensity
                                        totIraw += temp[e];
                                        peak_com_x += thisI * ((float) thisx); // for center of mass x
                                        peak_com_y += thisI * ((float) thisy); // for center of mass y
                                        //temp[e] = 0; // zero out this intensity so that we don't count it again
                                        inx[nat] = inx[p] + search_x[k];
                                        iny[nat] = iny[p] + search_y[k];
                                        peakpixel[e] = 1;
                                        if (nat < hitfinderMaxPixCount)
                                            peakpixels[nat] = e;
                                        if (thisI > maxI)
                                            maxI = thisI;
                                        if (thisI > maxIraw)
                                            maxIraw = temp[e];

                                        nat++;
                                    }
                                }
                            }
                        } while (lastnat != nat);

                        // Too many or too few pixels means ignore this 'peak'; move on now
                        if (nat < hitfinderMinPixCount || nat > hitfinderMaxPixCount) {
                            continue;
                        }

                        /*
                         *	Calculate center of mass for this peak from initial peak search
                         */
                        com_x = peak_com_x / fabs(totI);
                        com_y = peak_com_y / fabs(totI);
                        com_e = lrint(com_x) + lrint(com_y) * pix_nx;

                        long com_xi = lrint(com_x) - mi * asic_nx;
                        long com_yi = lrint(com_y) - mj * asic_ny;

                        /*
                         *	Calculate the local signal-to-noise ratio and local background in an annulus around this peak
                         *	(excluding pixels which look like they might be part of another peak)
                         */
                        float localSigma = 0;
                        float localOffset = 0;
                        long ringWidth = 2 * hitfinderLocalBGRadius;

                        float sumI = 0;
                        float sumIsquared = 0;
                        long np_sigma = 0;
                        long np_counted = 0;
                        float fbgr;
                        float backgroundMaxI = 0;
                        float fBackgroundThresh = 0;

                        for (long bj = -ringWidth; bj < ringWidth; bj++) {
                            for (long bi = -ringWidth; bi < ringWidth; bi++) {

                                // Within-ASIC check
                                if ((com_xi + bi) < 0)
                                    continue;
                                if ((com_xi + bi) >= asic_nx)
                                    continue;
                                if ((com_yi + bj) < 0)
                                    continue;
                                if ((com_yi + bj) >= asic_ny)
                                    continue;

                                // Within outer ring check
                                fbgr = sqrt(bi * bi + bj * bj);
                                if (fbgr > ringWidth)					// || fbgr <= hitfinderLocalBGRadius )				// || fbgr > hitfinderLocalBGRadius)
                                    continue;

                                // Position of this point in data stream
                                thisx = com_xi + bi + mi * asic_nx;
                                thisy = com_yi + bj + mj * asic_ny;
                                e = thisx + thisy * pix_nx;

                                thisr = lrint(pix_r[e]);
                                thisADCthresh = rthreshold[thisr];

                                // Intensity above background
                                thisI = temp[e];

                                // If above ADC threshold, this could be part of another peak
                                //if (temp[e] > thisADCthresh)
                                //	continue;

                                // Keep track of value and value-squared for offset and sigma calculation
                                // if(peakpixel[e] == 0 && mask[e] != 0) {
                                if (temp[e] < thisADCthresh && peakpixel[e] == 0 && mask[e] != 0) {
                                    np_sigma++;
                                    sumI += thisI;
                                    sumIsquared += (thisI * thisI);
                                    if (thisI > backgroundMaxI) {
                                        backgroundMaxI = thisI;
                                    }
                                }
                                np_counted += 1;
                            }
                        }

                        // Calculate local background and standard deviation
                        if (np_sigma != 0) {
                            localOffset = sumI / np_sigma;
                            localSigma = sqrt(sumIsquared / np_sigma - ((sumI / np_sigma) * (sumI / np_sigma)));
                        }
                        else {
                            localOffset = roffset[lrint(pix_r[lrint(com_e)])];
                            localSigma = 0.01;
                        }

                        /*
                         *	Re-integrate (and re-centroid) peak using local background estimates
                         */
                        totI = 0;
                        totIraw = 0;
                        maxI = 0;
                        maxIraw = 0;
                        peak_com_x = 0;
                        peak_com_y = 0;
                        for (long counter = 1; counter < nat && counter <= hitfinderMaxPixCount; counter++) {
                            e = peakpixels[counter];
                            thisIraw = temp[e];
                            thisI = thisIraw - localOffset;

                            totI += thisI;
                            totIraw += thisIraw;

                            // Remember that e = thisx + thisy*pix_nx;
                            ldiv_t xy = ldiv(e, pix_nx);
                            thisx = xy.rem;
                            thisy = xy.quot;
                            peak_com_x += thisI * ((float) thisx); // for center of mass x
                            peak_com_y += thisI * ((float) thisy); // for center of mass y

                            if (thisIraw > maxIraw)
                                maxIraw = thisIraw;
                            if (thisI > maxI)
                                maxI = thisI;
                        }
                        com_x = peak_com_x / fabs(totI);
                        com_y = peak_com_y / fabs(totI);
                        com_e = lrint(com_x) + lrint(com_y) * pix_nx;

                        /*
                         *	Calculate signal-to-noise and apply SNR criteria
                         */
                        snr = (float) (totI) / localSigma;
                        //snr = (float) (maxI)/localSigma;
                        //snr = (float) (totIraw-nat*localOffset)/localSigma;
                        //snr = (float) (maxIraw-localOffset)/localSigma;

                        // The more pixels there are in the peak, the more relaxed we are about this criterion
                        if (snr < hitfinderMinSNR)        //   - nat +hitfinderMinPixCount
                            continue;

                        // Is the maximum intensity in the peak enough above intensity in background region to be a peak and not noise?
                        // The more pixels there are in the peak, the more relaxed we are about this criterion
                        //fBackgroundThresh = hitfinderMinSNR - nat;
                        //if(fBackgroundThresh > 4) fBackgroundThresh = 4;
                        fBackgroundThresh = 1;
                        fBackgroundThresh *= (backgroundMaxI - localOffset);
                        if (maxI < fBackgroundThresh)
                            continue;

                        // This is a peak? If so, add info to peak list
                        if (nat >= hitfinderMinPixCount && nat <= hitfinderMaxPixCount) {

                            // This CAN happen!
                            if (totI == 0)
                                continue;

                            //com_x = peak_com_x/fabs(totI);
                            //com_y = peak_com_y/fabs(totI);

                            e = lrint(com_x) + lrint(com_y) * pix_nx;
                            if (e < 0 || e >= pix_nn) {
                                printf("Array bounds error: e=%ld\n", e);
                                continue;
                            }

                            // Remember peak information
                            if (peakCounter < hitfinderNpeaksMax) {
                                peaklist->peakNpix += nat;
                                peaklist->peakTotal += totI;
                                peaklist->peak_com_index[peakCounter] = e;
                                peaklist->peak_npix[peakCounter] = nat;
                                peaklist->peak_com_x[peakCounter] = com_x;
                                peaklist->peak_com_y[peakCounter] = com_y;
                                peaklist->peak_totalintensity[peakCounter] = totI;
                                peaklist->peak_maxintensity[peakCounter] = maxI;
                                peaklist->peak_sigma[peakCounter] = localSigma;
                                peaklist->peak_snr[peakCounter] = snr;
                                peakCounter++;
                                peaklist->nPeaks = peakCounter;
                            }
                            else {
                                peakCounter++;
                            }
                        }
                    }
                }
            }
        }
    }

    free(temp);
    free(inx);
    free(iny);
    free(peakpixel);
    free(peakpixels);

    free(roffset);
    free(rsigma);
    free(rcount);
    free(rthreshold);

    peaklist->nPeaks = peakCounter;
    return (peaklist->nPeaks);
    /*************************************************/

}


/*
 *	Create arrays for remembering Bragg peak data
 */
void allocatePeakList(tPeakList *peak, long NpeaksMax)
{
    peak->nPeaks = 0;
    peak->nPeaks_max = NpeaksMax;
    peak->nHot = 0;
    peak->peakResolution = 0;
    peak->peakResolutionA = 0;
    peak->peakDensity = 0;
    peak->peakNpix = 0;
    peak->peakTotal = 0;

    peak->peak_maxintensity = (float *) calloc(NpeaksMax, sizeof(float));
    peak->peak_totalintensity = (float *) calloc(NpeaksMax, sizeof(float));
    peak->peak_sigma = (float *) calloc(NpeaksMax, sizeof(float));
    peak->peak_snr = (float *) calloc(NpeaksMax, sizeof(float));
    peak->peak_npix = (float *) calloc(NpeaksMax, sizeof(float));
    peak->peak_com_x = (float *) calloc(NpeaksMax, sizeof(float));
    peak->peak_com_y = (float *) calloc(NpeaksMax, sizeof(float));
    peak->peak_com_index = (long *) calloc(NpeaksMax, sizeof(long));
    peak->peak_com_x_assembled = (float *) calloc(NpeaksMax, sizeof(float));
    peak->peak_com_y_assembled = (float *) calloc(NpeaksMax, sizeof(float));
    peak->peak_com_r_assembled = (float *) calloc(NpeaksMax, sizeof(float));
    peak->peak_com_q = (float *) calloc(NpeaksMax, sizeof(float));
    peak->peak_com_res = (float *) calloc(NpeaksMax, sizeof(float));
    peak->memoryAllocated = 1;
}

/*
 *	Clean up Bragg peak arrays
 */
void freePeakList(tPeakList peak)
{
    free(peak.peak_maxintensity);
    free(peak.peak_totalintensity);
    free(peak.peak_sigma);
    free(peak.peak_snr);
    free(peak.peak_npix);
    free(peak.peak_com_x);
    free(peak.peak_com_y);
    free(peak.peak_com_index);
    free(peak.peak_com_x_assembled);
    free(peak.peak_com_y_assembled);
    free(peak.peak_com_r_assembled);
    free(peak.peak_com_q);
    free(peak.peak_com_res);
    peak.memoryAllocated = 0;
}
