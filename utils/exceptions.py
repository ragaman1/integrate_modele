# utils/exceptions.py

class ImageGenerationError(Exception):
    """Base class for image generation errors."""
    pass

class NSFWContentError(ImageGenerationError):
    """Raised when the image contains NSFW content."""
    pass

class APIConnectionError(ImageGenerationError):
    """Raised when there is a connection issue with the API."""
    pass

class InvalidPromptError(ImageGenerationError):
    """Raised when the user's prompt is invalid."""
    pass