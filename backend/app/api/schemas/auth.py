from typing import Literal

from pydantic import BaseModel


class AuthConfigOut(BaseModel):
    auth_method: Literal["none", "basic"]


class EnableAuthRequest(BaseModel):
    username: str
    password: str


class DisableAuthRequest(BaseModel):
    current_password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    mfa_required: bool


class MfaVerifyRequest(BaseModel):
    code: str


class SessionInfo(BaseModel):
    username: str
    mfa_enabled: bool


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class MfaEnrollResponse(BaseModel):
    secret: str
    otpauth_uri: str
    qr_png_base64: str


class MfaEnrollConfirmRequest(BaseModel):
    secret: str
    code: str


class MfaDisableRequest(BaseModel):
    current_password: str
    code: str
