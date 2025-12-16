"""
Schemas package initialization.
"""
from app.schemas.common import (
    PaginationParams,
    PaginatedResponse,
    SuccessResponse,
    ErrorResponse,
    TaskResponse,
    BatchTaskResponse,
    HealthCheckResponse,
)
from app.schemas.lead import (
    LeadCreate,
    LeadUpdate,
    LeadResponse,
    LeadListQuery,
    LeadStatistics,
    BulkLeadOperation,
    CSVColumnMapping,
)
from app.schemas.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    TokenResponse,
    OTPVerification,
    OTPRequest,
    PasswordReset,
    PasswordChange,
)
from app.schemas.mail import (
    MailGenerateRequest,
    MailGenerateResponse,
    MailSaveRequest,
    MailSendRequest,
    MailSendResponse,
    BulkMailSendRequest,
    EmailTemplateCreate,
    EmailTemplateUpdate,
    EmailTemplateResponse,
)

__all__ = [
    # Common
    "PaginationParams",
    "PaginatedResponse",
    "SuccessResponse",
    "ErrorResponse",
    "TaskResponse",
    "BatchTaskResponse",
    "HealthCheckResponse",
    # Lead
    "LeadCreate",
    "LeadUpdate",
    "LeadResponse",
    "LeadListQuery",
    "LeadStatistics",
    "BulkLeadOperation",
    "CSVColumnMapping",
    # User
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "TokenResponse",
    "OTPVerification",
    "OTPRequest",
    "PasswordReset",
    "PasswordChange",
    # Mail
    "MailGenerateRequest",
    "MailGenerateResponse",
    "MailSaveRequest",
    "MailSendRequest",
    "MailSendResponse",
    "BulkMailSendRequest",
    "EmailTemplateCreate",
    "EmailTemplateUpdate",
    "EmailTemplateResponse",
]
