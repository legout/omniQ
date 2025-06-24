import dill
from typing import Any, TypeVar
import hmac
import hashlib
import os

T = TypeVar("T")

class DillSerializer:
    """Fallback serializer using dill for complex Python objects with security measures."""
    
    def __init__(self, secret_key: bytes | None = None):
        """
        Initializes the DillSerializer with an optional secret key for signature verification.
        
        Args:
            secret_key: Optional bytes key for HMAC signature. If None, a warning is issued and
                       deserialization will not verify signatures.
        """
        self.secret_key = secret_key or os.environ.get("OMNIQ_DILL_SECRET_KEY", "").encode()
        if not self.secret_key:
            print("WARNING: No secret key provided for DillSerializer. Deserialization will not be secure.")
    
    def serialize(self, obj: Any) -> bytes:
        """
        Serializes an object to bytes using dill, with an HMAC signature if a secret key is provided.
        
        Args:
            obj: The object to serialize.
            
        Returns:
            bytes: The serialized data with an optional HMAC signature prepended.
        """
        serialized_data = dill.dumps(obj)
        if self.secret_key:
            signature = hmac.new(self.secret_key, serialized_data, hashlib.sha256).digest()
            return signature + serialized_data
        return serialized_data
    
    def deserialize(self, data: bytes, type_hint: type[T] | None = None) -> T:
        """
        Deserializes bytes to an object using dill, with signature verification if a secret key is provided.
        
        Args:
            data: The bytes data to deserialize.
            type_hint: Optional type hint for deserialization (ignored for dill).
            
        Returns:
            The deserialized object.
            
        Raises:
            ValueError: If signature verification fails.
            dill.UnpicklingError: If deserialization fails.
        """
        if self.secret_key and len(data) > 32:
            signature = data[:32]
            serialized_data = data[32:]
            expected_signature = hmac.new(self.secret_key, serialized_data, hashlib.sha256).digest()
            if not hmac.compare_digest(signature, expected_signature):
                raise ValueError("Invalid HMAC signature. Data may have been tampered with.")
            return dill.loads(serialized_data)
        elif self.secret_key:
            raise ValueError("Data too short for HMAC signature verification.")
        else:
            return dill.loads(data)
