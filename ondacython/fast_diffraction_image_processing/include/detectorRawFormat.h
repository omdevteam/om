/*
 * datectorRawFormat.h
 *
 *  Created on: 09.03.2017
 *      Author: Yaro
 */

#ifndef DETECTORRAWFORMAT_H_
#define DETECTORRAWFORMAT_H_

#include <stdint.h>

typedef struct {
    uint16_t asic_nx;
    uint16_t asic_ny;
    uint8_t nasics_x;
    uint8_t nasics_y;

    uint16_t pix_nx;
    uint16_t pix_ny;
    uint32_t pix_nn;
} detectorRawFormat_t;


#endif /* DETECTORRAWFORMAT_H_ */
