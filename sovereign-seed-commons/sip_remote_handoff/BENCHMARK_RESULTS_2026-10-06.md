# SIP AF_XDP Zero-Copy Ingestion Benchmark

**Date:** 2026-10-06  
**Interface:** ens5f0np0 [Queue 0]  
**Worker Core:** CPU Core 2 (Pinned via pthread_setaffinity_np)  
**Daemon Status:** sip-node.service (Active)  

## Real-Time Ingress Telemetry
- **Total Packets Ingested:** 100,000 frames
- **Total Elapsed Duration:** 216.34 ms
- **Ingestion Throughput:** 462,235 kpps (~462.2 kpps)
- **Mean Ingestion Interval:** 2.16 µs / packet

## Pipeline Configuration
- **Kernel Bypass:** AF_XDP / XSK
- **Shared Memory:** Lock-free SPSC UMEM ring buffer
- **Memory Footprint:** 8.5 MB
