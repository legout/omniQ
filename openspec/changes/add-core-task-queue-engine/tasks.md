## 1. Implementation
- [x] 1.1 Create new `src/omniq/queue.py` file
- [x] 1.2 Implement AsyncTaskQueue class with enqueue/dequeue methods
- [x] 1.3 Move task scheduling logic from AsyncWorkerPool to AsyncTaskQueue
- [x] 1.4 Implement retry logic and exponential backoff in AsyncTaskQueue
- [x] 1.5 Update AsyncOmniQ to use AsyncTaskQueue instead of direct storage calls
- [x] 1.6 Update AsyncWorkerPool to use AsyncTaskQueue for task retrieval
- [x] 1.7 Add interval task rescheduling logic to AsyncTaskQueue
- [x] 1.8 Write tests for AsyncTaskQueue functionality
- [ ] 1.9 Update documentation to reflect new architecture