; optimized using intor by O.Y.
; Manually optimized with hdfsee
; Manually optimized with hdfsee
; Optimized by O.Y. now with correct res
; Optimized by O.Y., corrected distance between panels in ASICs
; Optimized panel offsets can be found at the end of the file
; Optimized panel offsets can be found at the end of the file
; Optimized panel offsets can be found at the end of the file
; Manually optimized with hdfsee
; geoptimized again using intor - O.Y.
; geoptimized using intor - O.Y.
; Manually optimized with hdfsee (only quadrants) - O.Y.
; Automatically generated from calibration data
clen =  /LCLS/detector_1/EncoderValue
coffset = 0.578086
;coffset = 0.587
;coffset = 0.586
;coffset = 0.585
;coffset = 0.584
;coffset = 0.583
;coffset = 0.582
;coffset = 0.581
;coffset = 0.580
;coffset = 0.579
;coffset = 0.578
photon_energy = /LCLS/photon_energy_eV
res = 9097.52
adu_per_eV = 0.00338

data = /entry_1/data_1/data
;mask = /entry_1/data_1/mask
mask_good = 0x0000
;mask_bad = 0xffff
dim0 = %
dim1 = ss
dim2 = fs

; The following lines define "rigid groups" which express the physical
; construction of the detector.  This is used when refining the detector
; geometry.

rigid_group_q0 = q0a0,q0a1,q0a2,q0a3,q0a4,q0a5,q0a6,q0a7,q0a8,q0a9,q0a10,q0a11,q0a12,q0a13,q0a14,q0a15
rigid_group_q1 = q1a0,q1a1,q1a2,q1a3,q1a4,q1a5,q1a6,q1a7,q1a8,q1a9,q1a10,q1a11,q1a12,q1a13,q1a14,q1a15
rigid_group_q2 = q2a0,q2a1,q2a2,q2a3,q2a4,q2a5,q2a6,q2a7,q2a8,q2a9,q2a10,q2a11,q2a12,q2a13,q2a14,q2a15
rigid_group_q3 = q3a0,q3a1,q3a2,q3a3,q3a4,q3a5,q3a6,q3a7,q3a8,q3a9,q3a10,q3a11,q3a12,q3a13,q3a14,q3a15

rigid_group_a0 = q0a0,q0a1
rigid_group_a1 = q0a2,q0a3
rigid_group_a2 = q0a4,q0a5
rigid_group_a3 = q0a6,q0a7
rigid_group_a4 = q0a8,q0a9
rigid_group_a5 = q0a10,q0a11
rigid_group_a6 = q0a12,q0a13
rigid_group_a7 = q0a14,q0a15
rigid_group_a8 = q1a0,q1a1
rigid_group_a9 = q1a2,q1a3
rigid_group_a10 = q1a4,q1a5
rigid_group_a11 = q1a6,q1a7
rigid_group_a12 = q1a8,q1a9
rigid_group_a13 = q1a10,q1a11
rigid_group_a14 = q1a12,q1a13
rigid_group_a15 = q1a14,q1a15
rigid_group_a16 = q2a0,q2a1
rigid_group_a17 = q2a2,q2a3
rigid_group_a18 = q2a4,q2a5
rigid_group_a19 = q2a6,q2a7
rigid_group_a20 = q2a8,q2a9
rigid_group_a21 = q2a10,q2a11
rigid_group_a22 = q2a12,q2a13
rigid_group_a23 = q2a14,q2a15
rigid_group_a24 = q3a0,q3a1
rigid_group_a25 = q3a2,q3a3
rigid_group_a26 = q3a4,q3a5
rigid_group_a27 = q3a6,q3a7
rigid_group_a28 = q3a8,q3a9
rigid_group_a29 = q3a10,q3a11
rigid_group_a30 = q3a12,q3a13
rigid_group_a31 = q3a14,q3a15

rigid_group_collection_quadrants = q0,q1,q2,q3
rigid_group_collection_asics = a0,a1,a2,a3,a4,a5,a6,a7,a8,a9,a10,a11,a12,a13,a14,a15,a16,a17,a18,a19,a20,a21,a22,a23,a24,a25,a26,a27,a28,a29,a30,a31

q0a0/min_fs = 0
q0a0/min_ss = 0
q0a0/max_fs = 193
q0a0/max_ss = 184
q0a0/res = 9090.91
q0a0/fs = +0.007107x +0.999975y
q0a0/ss = -0.999975x +0.007107y
q0a0/corner_x = 443.679
q0a0/corner_y = -27.2744

q0a1/min_fs = 194
q0a1/min_ss = 0
q0a1/max_fs = 387
q0a1/max_ss = 184
q0a1/res = 9090.91
q0a1/fs = +0.007107x +0.999975y
q0a1/ss = -0.999975x +0.007107y
q0a1/corner_x = 445.079
q0a1/corner_y = 169.721

q0a2/min_fs = 0
q0a2/min_ss = 185
q0a2/max_fs = 193
q0a2/max_ss = 369
q0a2/res = 9090.91
q0a2/fs = +0.004446x +0.999990y
q0a2/ss = -0.999990x +0.004446y
q0a2/corner_x = 236.725
q0a2/corner_y = -26.913

q0a3/min_fs = 194
q0a3/min_ss = 185
q0a3/max_fs = 387
q0a3/max_ss = 369
q0a3/res = 9090.91
q0a3/fs = +0.004446x +0.999990y
q0a3/ss = -0.999990x +0.004446y
q0a3/corner_x = 237.601
q0a3/corner_y = 170.085

q0a4/min_fs = 0
q0a4/min_ss = 370
q0a4/max_fs = 193
q0a4/max_ss = 554
q0a4/res = 9090.91
q0a4/fs = -0.999993x +0.003908y
q0a4/ss = -0.003908x -0.999993y
q0a4/corner_x = 870.1
q0a4/corner_y = 365.986

q0a5/min_fs = 194
q0a5/min_ss = 370
q0a5/max_fs = 387
q0a5/max_ss = 554
q0a5/res = 9090.91
q0a5/fs = -0.999993x +0.003908y
q0a5/ss = -0.003908x -0.999993y
q0a5/corner_x = 673.101
q0a5/corner_y = 366.756

q0a6/min_fs = 0
q0a6/min_ss = 555
q0a6/max_fs = 193
q0a6/max_ss = 739
q0a6/res = 9090.91
q0a6/fs = -0.999975x +0.007025y
q0a6/ss = -0.007025x -0.999975y
q0a6/corner_x = 868.86
q0a6/corner_y = 158.579

q0a7/min_fs = 194
q0a7/min_ss = 555
q0a7/max_fs = 387
q0a7/max_ss = 739
q0a7/res = 9090.91
q0a7/fs = -0.999975x +0.007025y
q0a7/ss = -0.007025x -0.999975y
q0a7/corner_x = 671.865
q0a7/corner_y = 159.963

q0a8/min_fs = 0
q0a8/min_ss = 740
q0a8/max_fs = 193
q0a8/max_ss = 924
q0a8/res = 9090.91
q0a8/fs = -0.006847x -0.999977y
q0a8/ss = +0.999977x -0.006847y
q0a8/corner_x = 479.437
q0a8/corner_y = 788.781

q0a9/min_fs = 194
q0a9/min_ss = 740
q0a9/max_fs = 387
q0a9/max_ss = 924
q0a9/res = 9090.91
q0a9/fs = -0.006847x -0.999977y
q0a9/ss = +0.999977x -0.006847y
q0a9/corner_x = 478.088
q0a9/corner_y = 591.786

q0a10/min_fs = 0
q0a10/min_ss = 925
q0a10/max_fs = 193
q0a10/max_ss = 1109
q0a10/res = 9090.91
q0a10/fs = -0.006141x -0.999980y
q0a10/ss = +0.999980x -0.006141y
q0a10/corner_x = 687.935
q0a10/corner_y = 788.59

q0a11/min_fs = 194
q0a11/min_ss = 925
q0a11/max_fs = 387
q0a11/max_ss = 1109
q0a11/res = 9090.91
q0a11/fs = -0.006141x -0.999980y
q0a11/ss = +0.999980x -0.006141y
q0a11/corner_x = 686.725
q0a11/corner_y = 591.594

q0a12/min_fs = 0
q0a12/min_ss = 1110
q0a12/max_fs = 193
q0a12/max_ss = 1294
q0a12/res = 9090.91
q0a12/fs = -0.999999x -0.001907y
q0a12/ss = +0.001907x -0.999999y
q0a12/corner_x = 449.061
q0a12/corner_y = 771.609

q0a13/min_fs = 194
q0a13/min_ss = 1110
q0a13/max_fs = 387
q0a13/max_ss = 1294
q0a13/res = 9090.91
q0a13/fs = -0.999999x -0.001907y
q0a13/ss = +0.001907x -0.999999y
q0a13/corner_x = 252.061
q0a13/corner_y = 771.233

q0a14/min_fs = 0
q0a14/min_ss = 1295
q0a14/max_fs = 193
q0a14/max_ss = 1479
q0a14/res = 9090.91
q0a14/fs = -0.999996x +0.002734y
q0a14/ss = -0.002734x -0.999996y
q0a14/corner_x = 445.181
q0a14/corner_y = 562.177

q0a15/min_fs = 194
q0a15/min_ss = 1295
q0a15/max_fs = 387
q0a15/max_ss = 1479
q0a15/res = 9090.91
q0a15/fs = -0.999996x +0.002734y
q0a15/ss = -0.002734x -0.999996y
q0a15/corner_x = 248.181
q0a15/corner_y = 562.716

q1a0/min_fs = 388
q1a0/min_ss = 0
q1a0/max_fs = 581
q1a0/max_ss = 184
q1a0/res = 9090.91
q1a0/fs = -0.999981x +0.006108y
q1a0/ss = -0.006108x -0.999981y
q1a0/corner_x = 37.2771
q1a0/corner_y = 446.84

q1a1/min_fs = 582
q1a1/min_ss = 0
q1a1/max_fs = 775
q1a1/max_ss = 184
q1a1/res = 9090.91
q1a1/fs = -0.999981x +0.006108y
q1a1/ss = -0.006108x -0.999981y
q1a1/corner_x = -159.719
q1a1/corner_y = 448.043

q1a2/min_fs = 388
q1a2/min_ss = 185
q1a2/max_fs = 581
q1a2/max_ss = 369
q1a2/res = 9090.91
q1a2/fs = -0.999991x +0.004248y
q1a2/ss = -0.004248x -0.999991y
q1a2/corner_x = 35.8783
q1a2/corner_y = 238.031

q1a3/min_fs = 582
q1a3/min_ss = 185
q1a3/max_fs = 775
q1a3/max_ss = 369
q1a3/res = 9090.91
q1a3/fs = -0.999991x +0.004248y
q1a3/ss = -0.004248x -0.999991y
q1a3/corner_x = -161.12
q1a3/corner_y = 238.868

q1a4/min_fs = 388
q1a4/min_ss = 370
q1a4/max_fs = 581
q1a4/max_ss = 554
q1a4/res = 9090.91
q1a4/fs = -0.008801x -0.999961y
q1a4/ss = +0.999961x -0.008801y
q1a4/corner_x = -355.354
q1a4/corner_y = 870.261

q1a5/min_fs = 582
q1a5/min_ss = 370
q1a5/max_fs = 775
q1a5/max_ss = 554
q1a5/res = 9090.91
q1a5/fs = -0.008801x -0.999961y
q1a5/ss = +0.999961x -0.008801y
q1a5/corner_x = -357.088
q1a5/corner_y = 673.268

q1a6/min_fs = 388
q1a6/min_ss = 555
q1a6/max_fs = 581
q1a6/max_ss = 739
q1a6/res = 9090.91
q1a6/fs = -0.001816x -0.999997y
q1a6/ss = +0.999997x -0.001816y
q1a6/corner_x = -149.279
q1a6/corner_y = 868.908

q1a7/min_fs = 582
q1a7/min_ss = 555
q1a7/max_fs = 775
q1a7/max_ss = 739
q1a7/res = 9090.91
q1a7/fs = -0.001816x -0.999997y
q1a7/ss = +0.999997x -0.001816y
q1a7/corner_x = -149.637
q1a7/corner_y = 671.908

q1a8/min_fs = 388
q1a8/min_ss = 740
q1a8/max_fs = 581
q1a8/max_ss = 924
q1a8/res = 9090.91
q1a8/fs = +1.000000x -0.000387y
q1a8/ss = +0.000387x +1.000000y
q1a8/corner_x = -780.217
q1a8/corner_y = 478.516

q1a9/min_fs = 582
q1a9/min_ss = 740
q1a9/max_fs = 775
q1a9/max_ss = 924
q1a9/res = 9090.91
q1a9/fs = +1.000000x -0.000387y
q1a9/ss = +0.000387x +1.000000y
q1a9/corner_x = -583.217
q1a9/corner_y = 478.44

q1a10/min_fs = 388
q1a10/min_ss = 925
q1a10/max_fs = 581
q1a10/max_ss = 1109
q1a10/res = 9090.91
q1a10/fs = +0.999998x -0.002355y
q1a10/ss = +0.002355x +0.999998y
q1a10/corner_x = -780.82
q1a10/corner_y = 687.414

q1a11/min_fs = 582
q1a11/min_ss = 925
q1a11/max_fs = 775
q1a11/max_ss = 1109
q1a11/res = 9090.91
q1a11/fs = +0.999998x -0.002355y
q1a11/ss = +0.002355x +0.999998y
q1a11/corner_x = -583.82
q1a11/corner_y = 686.95

q1a12/min_fs = 388
q1a12/min_ss = 1110
q1a12/max_fs = 581
q1a12/max_ss = 1294
q1a12/res = 9090.91
q1a12/fs = -0.000791x -1.000000y
q1a12/ss = +1.000000x -0.000791y
q1a12/corner_x = -759.887
q1a12/corner_y = 447.406

q1a13/min_fs = 582
q1a13/min_ss = 1110
q1a13/max_fs = 775
q1a13/max_ss = 1294
q1a13/res = 9090.91
q1a13/fs = -0.000791x -1.000000y
q1a13/ss = +1.000000x -0.000791y
q1a13/corner_x = -760.043
q1a13/corner_y = 250.406

q1a14/min_fs = 388
q1a14/min_ss = 1295
q1a14/max_fs = 581
q1a14/max_ss = 1479
q1a14/res = 9090.91
q1a14/fs = -0.004033x -0.999991y
q1a14/ss = +0.999991x -0.004033y
q1a14/corner_x = -551.415
q1a14/corner_y = 448

q1a15/min_fs = 582
q1a15/min_ss = 1295
q1a15/max_fs = 775
q1a15/max_ss = 1479
q1a15/res = 9090.91
q1a15/fs = -0.004033x -0.999991y
q1a15/ss = +0.999991x -0.004033y
q1a15/corner_x = -552.209
q1a15/corner_y = 251.002

q2a0/min_fs = 776
q2a0/min_ss = 0
q2a0/max_fs = 969
q2a0/max_ss = 184
q2a0/res = 9090.91
q2a0/fs = +0.002600x -0.999997y
q2a0/ss = +0.999997x +0.002600y
q2a0/corner_x = -438.708
q2a0/corner_y = 38.5129

q2a1/min_fs = 970
q2a1/min_ss = 0
q2a1/max_fs = 1163
q2a1/max_ss = 184
q2a1/res = 9090.91
q2a1/fs = +0.002600x -0.999997y
q2a1/ss = +0.999997x +0.002600y
q2a1/corner_x = -438.196
q2a1/corner_y = -158.487

q2a2/min_fs = 776
q2a2/min_ss = 185
q2a2/max_fs = 969
q2a2/max_ss = 369
q2a2/res = 9090.91
q2a2/fs = -0.000787x -0.999999y
q2a2/ss = +0.999999x -0.000787y
q2a2/corner_x = -231.351
q2a2/corner_y = 37.7978

q2a3/min_fs = 970
q2a3/min_ss = 185
q2a3/max_fs = 1163
q2a3/max_ss = 369
q2a3/res = 9090.91
q2a3/fs = -0.000787x -0.999999y
q2a3/ss = +0.999999x -0.000787y
q2a3/corner_x = -231.506
q2a3/corner_y = -159.202

q2a4/min_fs = 776
q2a4/min_ss = 370
q2a4/max_fs = 969
q2a4/max_ss = 554
q2a4/res = 9090.91
q2a4/fs = +0.999983x +0.005961y
q2a4/ss = -0.005961x +0.999983y
q2a4/corner_x = -862.933
q2a4/corner_y = -352.962

q2a5/min_fs = 970
q2a5/min_ss = 370
q2a5/max_fs = 1163
q2a5/max_ss = 554
q2a5/res = 9090.91
q2a5/fs = +0.999983x +0.005961y
q2a5/ss = -0.005961x +0.999983y
q2a5/corner_x = -665.936
q2a5/corner_y = -351.787

q2a6/min_fs = 776
q2a6/min_ss = 555
q2a6/max_fs = 969
q2a6/max_ss = 739
q2a6/res = 9090.91
q2a6/fs = +0.999999x -0.000424y
q2a6/ss = +0.000424x +0.999999y
q2a6/corner_x = -863.161
q2a6/corner_y = -147.168

q2a7/min_fs = 970
q2a7/min_ss = 555
q2a7/max_fs = 1163
q2a7/max_ss = 739
q2a7/res = 9090.91
q2a7/fs = +0.999999x -0.000424y
q2a7/ss = +0.000424x +0.999999y
q2a7/corner_x = -666.161
q2a7/corner_y = -147.252

q2a8/min_fs = 776
q2a8/min_ss = 740
q2a8/max_fs = 969
q2a8/max_ss = 924
q2a8/res = 9090.91
q2a8/fs = +0.001653x +0.999999y
q2a8/ss = -0.999999x +0.001653y
q2a8/corner_x = -472.705
q2a8/corner_y = -775.755

q2a9/min_fs = 970
q2a9/min_ss = 740
q2a9/max_fs = 1163
q2a9/max_ss = 924
q2a9/res = 9090.91
q2a9/fs = +0.001653x +0.999999y
q2a9/ss = -0.999999x +0.001653y
q2a9/corner_x = -472.38
q2a9/corner_y = -578.755

q2a10/min_fs = 776
q2a10/min_ss = 925
q2a10/max_fs = 969
q2a10/max_ss = 1109
q2a10/res = 9090.91
q2a10/fs = -0.001793x +0.999998y
q2a10/ss = -0.999998x -0.001793y
q2a10/corner_x = -676.191
q2a10/corner_y = -775.088

q2a11/min_fs = 970
q2a11/min_ss = 925
q2a11/max_fs = 1163
q2a11/max_ss = 1109
q2a11/res = 9090.91
q2a11/fs = -0.001793x +0.999998y
q2a11/ss = -0.999998x -0.001793y
q2a11/corner_x = -676.544
q2a11/corner_y = -578.089

q2a12/min_fs = 776
q2a12/min_ss = 1110
q2a12/max_fs = 969
q2a12/max_ss = 1294
q2a12/res = 9090.91
q2a12/fs = +0.999999x -0.001815y
q2a12/ss = +0.001815x +0.999999y
q2a12/corner_x = -436.82
q2a12/corner_y = -754.733

q2a13/min_fs = 970
q2a13/min_ss = 1110
q2a13/max_fs = 1163
q2a13/max_ss = 1294
q2a13/res = 9090.91
q2a13/fs = +0.999999x -0.001815y
q2a13/ss = +0.001815x +0.999999y
q2a13/corner_x = -239.82
q2a13/corner_y = -755.09

q2a14/min_fs = 776
q2a14/min_ss = 1295
q2a14/max_fs = 969
q2a14/max_ss = 1479
q2a14/res = 9090.91
q2a14/fs = +1.000001x +0.000813y
q2a14/ss = -0.000813x +1.000001y
q2a14/corner_x = -436.46
q2a14/corner_y = -549.521

q2a15/min_fs = 970
q2a15/min_ss = 1295
q2a15/max_fs = 1163
q2a15/max_ss = 1479
q2a15/res = 9090.91
q2a15/fs = +1.000001x +0.000813y
q2a15/ss = -0.000813x +1.000001y
q2a15/corner_x = -239.46
q2a15/corner_y = -549.361

q3a0/min_fs = 1164
q3a0/min_ss = 0
q3a0/max_fs = 1357
q3a0/max_ss = 184
q3a0/res = 9090.91
q3a0/fs = +0.999997x -0.002153y
q3a0/ss = +0.002153x +0.999997y
q3a0/corner_x = -31.218
q3a0/corner_y = -434.791

q3a1/min_fs = 1358
q3a1/min_ss = 0
q3a1/max_fs = 1551
q3a1/max_ss = 184
q3a1/res = 9090.91
q3a1/fs = +0.999997x -0.002153y
q3a1/ss = +0.002153x +0.999997y
q3a1/corner_x = 165.781
q3a1/corner_y = -435.215

q3a2/min_fs = 1164
q3a2/min_ss = 185
q3a2/max_fs = 1357
q3a2/max_ss = 369
q3a2/res = 9090.91
q3a2/fs = +0.999980x -0.006363y
q3a2/ss = +0.006363x +0.999980y
q3a2/corner_x = -32.8592
q3a2/corner_y = -229.718

q3a3/min_fs = 1358
q3a3/min_ss = 185
q3a3/max_fs = 1551
q3a3/max_ss = 369
q3a3/res = 9090.91
q3a3/fs = +0.999980x -0.006363y
q3a3/ss = +0.006363x +0.999980y
q3a3/corner_x = 164.137
q3a3/corner_y = -230.971

q3a4/min_fs = 1164
q3a4/min_ss = 370
q3a4/max_fs = 1357
q3a4/max_ss = 554
q3a4/res = 9090.91
q3a4/fs = +0.002693x +0.999996y
q3a4/ss = -0.999996x +0.002693y
q3a4/corner_x = 361.562
q3a4/corner_y = -860.283

q3a5/min_fs = 1358
q3a5/min_ss = 370
q3a5/max_fs = 1551
q3a5/max_ss = 554
q3a5/res = 9090.91
q3a5/fs = +0.002693x +0.999996y
q3a5/ss = -0.999996x +0.002693y
q3a5/corner_x = 362.093
q3a5/corner_y = -663.284

q3a6/min_fs = 1164
q3a6/min_ss = 555
q3a6/max_fs = 1357
q3a6/max_ss = 739
q3a6/res = 9090.91
q3a6/fs = -0.003642x +0.999993y
q3a6/ss = -0.999993x -0.003642y
q3a6/corner_x = 159.717
q3a6/corner_y = -858.878

q3a7/min_fs = 1358
q3a7/min_ss = 555
q3a7/max_fs = 1551
q3a7/max_ss = 739
q3a7/res = 9090.91
q3a7/fs = -0.003642x +0.999993y
q3a7/ss = -0.999993x -0.003642y
q3a7/corner_x = 159
q3a7/corner_y = -661.88

q3a8/min_fs = 1164
q3a8/min_ss = 740
q3a8/max_fs = 1357
q3a8/max_ss = 924
q3a8/res = 9090.91
q3a8/fs = -0.999980x +0.006075y
q3a8/ss = -0.006075x -0.999980y
q3a8/corner_x = 784.913
q3a8/corner_y = -470.409

q3a9/min_fs = 1358
q3a9/min_ss = 740
q3a9/max_fs = 1551
q3a9/max_ss = 924
q3a9/res = 9090.91
q3a9/fs = -0.999980x +0.006075y
q3a9/ss = -0.006075x -0.999980y
q3a9/corner_x = 587.917
q3a9/corner_y = -469.213

q3a10/min_fs = 1164
q3a10/min_ss = 925
q3a10/max_fs = 1357
q3a10/max_ss = 1109
q3a10/res = 9090.91
q3a10/fs = -0.999981x +0.006080y
q3a10/ss = -0.006080x -0.999981y
q3a10/corner_x = 783.372
q3a10/corner_y = -676.278

q3a11/min_fs = 1358
q3a11/min_ss = 925
q3a11/max_fs = 1551
q3a11/max_ss = 1109
q3a11/res = 9090.91
q3a11/fs = -0.999981x +0.006080y
q3a11/ss = -0.006080x -0.999981y
q3a11/corner_x = 586.376
q3a11/corner_y = -675.081

q3a12/min_fs = 1164
q3a12/min_ss = 1110
q3a12/max_fs = 1357
q3a12/max_ss = 1294
q3a12/res = 9090.91
q3a12/fs = +0.004795x +0.999989y
q3a12/ss = -0.999989x +0.004795y
q3a12/corner_x = 762.679
q3a12/corner_y = -436.769

q3a13/min_fs = 1358
q3a13/min_ss = 1110
q3a13/max_fs = 1551
q3a13/max_ss = 1294
q3a13/res = 9090.91
q3a13/fs = +0.004795x +0.999989y
q3a13/ss = -0.999989x +0.004795y
q3a13/corner_x = 763.624
q3a13/corner_y = -239.771

q3a14/min_fs = 1164
q3a14/min_ss = 1295
q3a14/max_fs = 1357
q3a14/max_ss = 1479
q3a14/res = 9090.91
q3a14/fs = +0.000153x +1.000000y
q3a14/ss = -1.000000x +0.000153y
q3a14/corner_x = 556.709
q3a14/corner_y = -436.084

q3a15/min_fs = 1358
q3a15/min_ss = 1295
q3a15/max_fs = 1551
q3a15/max_ss = 1479
q3a15/res = 9090.91
q3a15/fs = +0.000153x +1.000000y
q3a15/ss = -1.000000x +0.000153y
q3a15/corner_x = 556.739
q3a15/corner_y = -239.084
