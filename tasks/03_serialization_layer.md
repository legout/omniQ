# Task 3: Serialization Layer

## Objective
Implement a flexible and high-performance serialization layer for the OmniQ library. This layer will be responsible for converting tasks and results into a format suitable for storage and transmitting them between workers. The implementation will follow a dual-serializer strategy, using `msgspec` for performance and `dill` as a fallback for complex Python objects.

## Requirements

### 1. Base Serializer Interface (`src/omniq/serialization/base.py`)
- Create a `base.py` file in the `src/omniq/serialization/` directory.
- Define a `BaseSerializer` abstract base class (ABC).
- This interface must declare two methods:
    - `serialize(obj: Any) -> bytes`: Converts a Python object into bytes.
    - `deserialize(data: bytes) -> Any`: Converts bytes back into a Python object.

### 2. `msgspec` Serializer (`src/omniq/serialization/msgspec.py`)
- Create a `msgspec.py` file in the `src/omniq/serialization/` directory.
- Implement a `MsgspecSerializer` class that inherits from `BaseSerializer`.
- This class will use the `msgspec` library to perform serialization and deserialization.
- It should be optimized for performance and handle all `msgspec`-compatible types.

### 3. `dill` Serializer (`src/omniq/serialization/dill.py`)
- Create a `dill.py` file in the `src/omniq/serialization/` directory.
- Implement a `DillSerializer` class that inherits from `BaseSerializer`.
- This class will use the `dill` library, serving as a fallback for serializing complex Python objects that `msgspec` cannot handle (e.g., functions with closures, lambdas).
- Ensure security measures are considered for `dill` deserialization, as it can execute arbitrary code.

### 4. Serialization Manager (`src/omniq/serialization/manager.py`)
- Create a `manager.py` file in the `src/omniq/serialization/` directory.
- Implement a `SerializationManager` class.
- This manager will orchestrate the serialization strategy.
- It should contain a mechanism to detect which serializer to use for a given object. The default should be `MsgspecSerializer` for performance, with a fallback to `DillSerializer` for incompatible types.
- The manager should embed the name of the serializer used (e.g., 'msgspec' or 'dill') into the serialized data, so the deserialization process knows which decoder to use.

## Completion Criteria
- The `src/omniq/serialization/` directory contains `base.py`, `msgspec.py`, `dill.py`, and `manager.py`.
- The `BaseSerializer` interface is correctly defined.
- `MsgspecSerializer` and `DillSerializer` are implemented and functional.
- The `SerializationManager` is implemented and can correctly choose the appropriate serializer, serialize the data with metadata, and deserialize it.