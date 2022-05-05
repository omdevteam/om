#!/usr/bin/env python
from mpi4py import MPI
import socket
import time
import os
import contextlib

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

total_time = 30

if rank == 0:
    print(f"Running diagnostic test. Esitmated time: {total_time} sec")
    data = {'test': True}
    print(f"Total MPI ranks: {size}")
    timestart = time.time()
    answers = []
    next_report = 5
    while True:
        if comm.Iprobe(source=MPI.ANY_SOURCE):
            recv_msg = comm.recv(source=MPI.ANY_SOURCE)
            answers.append(recv_msg)
        timenow = time.time()
        if timenow-timestart > next_report:
            print(f"Running: {next_report}/{total_time} sec")
            next_report = next_report + 5
        if timenow-timestart > total_time:
            break
    print("Test finished")
    any_failed = False
    for rank_num in range(1, size):
        if not rank_num in answers:
            any_failed = True
            print(f"Rank {rank_num} could not run the test. See at the top of the output where it is running")
    if any_failed == True:
        print("Aborting")
        comm.Abort()
    else:
        print(f"All {size} ranks could run the test")
    MPI.Finalize()
elif rank !=0:
    print(f"MPI rank {rank} is running on {socket.gethostname()}")
    from psana import *
    ds = DataSource('shmem=psana.0:stop=no')
    evt = next(ds.events())
    comm.send(rank, dest=0)
    MPI.Finalize()
