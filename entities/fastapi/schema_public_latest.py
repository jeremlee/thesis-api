from __future__ import annotations

import datetime
import uuid
from typing import (
    Annotated,
    Any,
    List,
    Literal,
    NotRequired,
    Optional,
    TypeAlias,
    TypedDict,
)

from pydantic import BaseModel, Field, Json

NetRequestStatus: TypeAlias = Literal["PENDING", "SUCCESS", "ERROR"]

RealtimeEqualityOp: TypeAlias = Literal["eq", "neq", "lt", "lte", "gt", "gte", "in"]

RealtimeAction: TypeAlias = Literal["INSERT", "UPDATE", "DELETE", "TRUNCATE", "ERROR"]

StorageBuckettype: TypeAlias = Literal["STANDARD", "ANALYTICS", "VECTOR"]

AuthFactorType: TypeAlias = Literal["totp", "webauthn", "phone"]

AuthFactorStatus: TypeAlias = Literal["unverified", "verified"]

AuthAalLevel: TypeAlias = Literal["aal1", "aal2", "aal3"]

AuthCodeChallengeMethod: TypeAlias = Literal["s256", "plain"]

AuthOneTimeTokenType: TypeAlias = Literal["confirmation_token", "reauthentication_token", "recovery_token", "email_change_token_new", "email_change_token_current", "phone_change_token"]

AuthOauthRegistrationType: TypeAlias = Literal["dynamic", "manual"]

AuthOauthAuthorizationStatus: TypeAlias = Literal["pending", "approved", "denied", "expired"]

AuthOauthResponseType: TypeAlias = Literal["code"]

AuthOauthClientType: TypeAlias = Literal["public", "confidential"]

PublicActionType: TypeAlias = Literal["create", "update", "delete"]

PublicAuditEntityType: TypeAlias = Literal["Applicant", "Job Listing", "Admin Feedback", "Staff Evaluation", "Staff"]

PublicAuditEventType: TypeAlias = Literal["Joblisting modified", "Joblisting deleted", "Created joblisting", "Applied for job", "Changed user role", "Changed candidate status", "Admin feedback created", "Admin feedback deleted", "Admin feedback updated", "Created Staff Evaluation", "Deleted Staff Evaluation", "Updated Staff Evaluation", "Created staff account", "Staff password updated"]

PublicCandidateStatus: TypeAlias = Literal["Paper Screening", "Exam", "HR Interview", "Technical Interview", "Final Interview", "Job Offer", "Accepted Job Offer", "Close Status"]

PublicUserRoles: TypeAlias = Literal["SuperAdmin", "Admin", "Staff", "Applicant"]

class PublicAdminFeedback(BaseModel):
    admin_id: uuid.UUID = Field(alias="admin_id")
    applicant_id: uuid.UUID = Field(alias="applicant_id")
    created_at: datetime.datetime = Field(alias="created_at")
    feedback: Optional[str] = Field(alias="feedback")
    id: uuid.UUID = Field(alias="id")

class PublicAdminFeedbackInsert(TypedDict):
    admin_id: NotRequired[Annotated[uuid.UUID, Field(alias="admin_id")]]
    applicant_id: NotRequired[Annotated[uuid.UUID, Field(alias="applicant_id")]]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    feedback: NotRequired[Annotated[Optional[str], Field(alias="feedback")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]

class PublicAdminFeedbackUpdate(TypedDict):
    admin_id: NotRequired[Annotated[uuid.UUID, Field(alias="admin_id")]]
    applicant_id: NotRequired[Annotated[uuid.UUID, Field(alias="applicant_id")]]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    feedback: NotRequired[Annotated[Optional[str], Field(alias="feedback")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]

class PublicApplicantSkills(BaseModel):
    applicant_id: uuid.UUID = Field(alias="applicant_id")
    created_at: datetime.datetime = Field(alias="created_at")
    id: uuid.UUID = Field(alias="id")
    rating: int = Field(alias="rating")
    tag_id: int = Field(alias="tag_id")

class PublicApplicantSkillsInsert(TypedDict):
    applicant_id: Annotated[uuid.UUID, Field(alias="applicant_id")]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    rating: NotRequired[Annotated[int, Field(alias="rating")]]
    tag_id: Annotated[int, Field(alias="tag_id")]

class PublicApplicantSkillsUpdate(TypedDict):
    applicant_id: NotRequired[Annotated[uuid.UUID, Field(alias="applicant_id")]]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    rating: NotRequired[Annotated[int, Field(alias="rating")]]
    tag_id: NotRequired[Annotated[int, Field(alias="tag_id")]]

class PublicApplicants(BaseModel):
    city: Optional[str] = Field(alias="city")
    contact_number: Optional[str] = Field(alias="contact_number")
    created_at: datetime.datetime = Field(alias="created_at")
    email: Optional[str] = Field(alias="email")
    first_name: str = Field(alias="first_name")
    id: uuid.UUID = Field(alias="id")
    joblisting_id: uuid.UUID = Field(alias="joblisting_id")
    last_name: str = Field(alias="last_name")
    parsed_resume_id: Optional[uuid.UUID] = Field(alias="parsed_resume_id")
    platform: Optional[str] = Field(alias="platform")
    resume_id: str = Field(alias="resume_id")
    scheduled_at: Optional[datetime.datetime] = Field(alias="scheduled_at")
    score_id: Optional[uuid.UUID] = Field(alias="score_id")
    state: Optional[str] = Field(alias="state")
    status: PublicCandidateStatus = Field(alias="status")
    street: Optional[str] = Field(alias="street")
    transcribed_id: Optional[uuid.UUID] = Field(alias="transcribed_id")
    transcript_id: str = Field(alias="transcript_id")
    zip: Optional[str] = Field(alias="zip")

class PublicApplicantsInsert(TypedDict):
    city: NotRequired[Annotated[Optional[str], Field(alias="city")]]
    contact_number: NotRequired[Annotated[Optional[str], Field(alias="contact_number")]]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    email: NotRequired[Annotated[Optional[str], Field(alias="email")]]
    first_name: Annotated[str, Field(alias="first_name")]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    joblisting_id: Annotated[uuid.UUID, Field(alias="joblisting_id")]
    last_name: Annotated[str, Field(alias="last_name")]
    parsed_resume_id: NotRequired[Annotated[Optional[uuid.UUID], Field(alias="parsed_resume_id")]]
    platform: NotRequired[Annotated[Optional[str], Field(alias="platform")]]
    resume_id: Annotated[str, Field(alias="resume_id")]
    scheduled_at: NotRequired[Annotated[Optional[datetime.datetime], Field(alias="scheduled_at")]]
    score_id: NotRequired[Annotated[Optional[uuid.UUID], Field(alias="score_id")]]
    state: NotRequired[Annotated[Optional[str], Field(alias="state")]]
    status: NotRequired[Annotated[PublicCandidateStatus, Field(alias="status")]]
    street: NotRequired[Annotated[Optional[str], Field(alias="street")]]
    transcribed_id: NotRequired[Annotated[Optional[uuid.UUID], Field(alias="transcribed_id")]]
    transcript_id: Annotated[str, Field(alias="transcript_id")]
    zip: NotRequired[Annotated[Optional[str], Field(alias="zip")]]

class PublicApplicantsUpdate(TypedDict):
    city: NotRequired[Annotated[Optional[str], Field(alias="city")]]
    contact_number: NotRequired[Annotated[Optional[str], Field(alias="contact_number")]]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    email: NotRequired[Annotated[Optional[str], Field(alias="email")]]
    first_name: NotRequired[Annotated[str, Field(alias="first_name")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    joblisting_id: NotRequired[Annotated[uuid.UUID, Field(alias="joblisting_id")]]
    last_name: NotRequired[Annotated[str, Field(alias="last_name")]]
    parsed_resume_id: NotRequired[Annotated[Optional[uuid.UUID], Field(alias="parsed_resume_id")]]
    platform: NotRequired[Annotated[Optional[str], Field(alias="platform")]]
    resume_id: NotRequired[Annotated[str, Field(alias="resume_id")]]
    scheduled_at: NotRequired[Annotated[Optional[datetime.datetime], Field(alias="scheduled_at")]]
    score_id: NotRequired[Annotated[Optional[uuid.UUID], Field(alias="score_id")]]
    state: NotRequired[Annotated[Optional[str], Field(alias="state")]]
    status: NotRequired[Annotated[PublicCandidateStatus, Field(alias="status")]]
    street: NotRequired[Annotated[Optional[str], Field(alias="street")]]
    transcribed_id: NotRequired[Annotated[Optional[uuid.UUID], Field(alias="transcribed_id")]]
    transcript_id: NotRequired[Annotated[str, Field(alias="transcript_id")]]
    zip: NotRequired[Annotated[Optional[str], Field(alias="zip")]]

class PublicAuditLogs(BaseModel):
    action: PublicActionType = Field(alias="action")
    actor_id: Optional[uuid.UUID] = Field(alias="actor_id")
    actor_type: PublicUserRoles = Field(alias="actor_type")
    changes: Json[Any] = Field(alias="changes")
    created_at: datetime.datetime = Field(alias="created_at")
    details: str = Field(alias="details")
    entity_id: uuid.UUID = Field(alias="entity_id")
    entity_type: PublicAuditEntityType = Field(alias="entity_type")
    event_type: PublicAuditEventType = Field(alias="event_type")
    id: uuid.UUID = Field(alias="id")

class PublicAuditLogsInsert(TypedDict):
    action: Annotated[PublicActionType, Field(alias="action")]
    actor_id: NotRequired[Annotated[Optional[uuid.UUID], Field(alias="actor_id")]]
    actor_type: Annotated[PublicUserRoles, Field(alias="actor_type")]
    changes: NotRequired[Annotated[Json[Any], Field(alias="changes")]]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    details: Annotated[str, Field(alias="details")]
    entity_id: Annotated[uuid.UUID, Field(alias="entity_id")]
    entity_type: Annotated[PublicAuditEntityType, Field(alias="entity_type")]
    event_type: Annotated[PublicAuditEventType, Field(alias="event_type")]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]

class PublicAuditLogsUpdate(TypedDict):
    action: NotRequired[Annotated[PublicActionType, Field(alias="action")]]
    actor_id: NotRequired[Annotated[Optional[uuid.UUID], Field(alias="actor_id")]]
    actor_type: NotRequired[Annotated[PublicUserRoles, Field(alias="actor_type")]]
    changes: NotRequired[Annotated[Json[Any], Field(alias="changes")]]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    details: NotRequired[Annotated[str, Field(alias="details")]]
    entity_id: NotRequired[Annotated[uuid.UUID, Field(alias="entity_id")]]
    entity_type: NotRequired[Annotated[PublicAuditEntityType, Field(alias="entity_type")]]
    event_type: NotRequired[Annotated[PublicAuditEventType, Field(alias="event_type")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]

class PublicConversationMessages(BaseModel):
    conversation_id: uuid.UUID = Field(alias="conversation_id")
    created_at: datetime.datetime = Field(alias="created_at")
    id: uuid.UUID = Field(alias="id")
    message: str = Field(alias="message")
    role: str = Field(alias="role")

class PublicConversationMessagesInsert(TypedDict):
    conversation_id: Annotated[uuid.UUID, Field(alias="conversation_id")]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    message: Annotated[str, Field(alias="message")]
    role: Annotated[str, Field(alias="role")]

class PublicConversationMessagesUpdate(TypedDict):
    conversation_id: NotRequired[Annotated[uuid.UUID, Field(alias="conversation_id")]]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    message: NotRequired[Annotated[str, Field(alias="message")]]
    role: NotRequired[Annotated[str, Field(alias="role")]]

class PublicHrReports(BaseModel):
    applicant_id: uuid.UUID = Field(alias="applicant_id")
    candidate_status: PublicCandidateStatus = Field(alias="candidate_status")
    created_at: datetime.datetime = Field(alias="created_at")
    file_pathname: Optional[str] = Field(alias="file_pathname")
    id: uuid.UUID = Field(alias="id")
    score: float = Field(alias="score")
    staff_id: uuid.UUID = Field(alias="staff_id")
    summary: str = Field(alias="summary")

class PublicHrReportsInsert(TypedDict):
    applicant_id: NotRequired[Annotated[uuid.UUID, Field(alias="applicant_id")]]
    candidate_status: NotRequired[Annotated[PublicCandidateStatus, Field(alias="candidate_status")]]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    file_pathname: NotRequired[Annotated[Optional[str], Field(alias="file_pathname")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    score: Annotated[float, Field(alias="score")]
    staff_id: NotRequired[Annotated[uuid.UUID, Field(alias="staff_id")]]
    summary: Annotated[str, Field(alias="summary")]

class PublicHrReportsUpdate(TypedDict):
    applicant_id: NotRequired[Annotated[uuid.UUID, Field(alias="applicant_id")]]
    candidate_status: NotRequired[Annotated[PublicCandidateStatus, Field(alias="candidate_status")]]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    file_pathname: NotRequired[Annotated[Optional[str], Field(alias="file_pathname")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    score: NotRequired[Annotated[float, Field(alias="score")]]
    staff_id: NotRequired[Annotated[uuid.UUID, Field(alias="staff_id")]]
    summary: NotRequired[Annotated[str, Field(alias="summary")]]

class PublicJlQualifications(BaseModel):
    id: uuid.UUID = Field(alias="id")
    joblisting_id: uuid.UUID = Field(alias="joblisting_id")
    qualification: str = Field(alias="qualification")

class PublicJlQualificationsInsert(TypedDict):
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    joblisting_id: Annotated[uuid.UUID, Field(alias="joblisting_id")]
    qualification: Annotated[str, Field(alias="qualification")]

class PublicJlQualificationsUpdate(TypedDict):
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    joblisting_id: NotRequired[Annotated[uuid.UUID, Field(alias="joblisting_id")]]
    qualification: NotRequired[Annotated[str, Field(alias="qualification")]]

class PublicJlRequirements(BaseModel):
    id: uuid.UUID = Field(alias="id")
    joblisting_id: uuid.UUID = Field(alias="joblisting_id")
    requirement: str = Field(alias="requirement")

class PublicJlRequirementsInsert(TypedDict):
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    joblisting_id: Annotated[uuid.UUID, Field(alias="joblisting_id")]
    requirement: Annotated[str, Field(alias="requirement")]

class PublicJlRequirementsUpdate(TypedDict):
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    joblisting_id: NotRequired[Annotated[uuid.UUID, Field(alias="joblisting_id")]]
    requirement: NotRequired[Annotated[str, Field(alias="requirement")]]

class PublicJobListings(BaseModel):
    created_at: datetime.datetime = Field(alias="created_at")
    created_by: uuid.UUID = Field(alias="created_by")
    id: uuid.UUID = Field(alias="id")
    is_fulltime: bool = Field(alias="is_fulltime")
    location: str = Field(alias="location")
    staff_id: Optional[uuid.UUID] = Field(alias="staff_id")
    title: str = Field(alias="title")

class PublicJobListingsInsert(TypedDict):
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    created_by: Annotated[uuid.UUID, Field(alias="created_by")]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    is_fulltime: NotRequired[Annotated[bool, Field(alias="is_fulltime")]]
    location: Annotated[str, Field(alias="location")]
    staff_id: NotRequired[Annotated[Optional[uuid.UUID], Field(alias="staff_id")]]
    title: Annotated[str, Field(alias="title")]

class PublicJobListingsUpdate(TypedDict):
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    created_by: NotRequired[Annotated[uuid.UUID, Field(alias="created_by")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    is_fulltime: NotRequired[Annotated[bool, Field(alias="is_fulltime")]]
    location: NotRequired[Annotated[str, Field(alias="location")]]
    staff_id: NotRequired[Annotated[Optional[uuid.UUID], Field(alias="staff_id")]]
    title: NotRequired[Annotated[str, Field(alias="title")]]

class PublicJobTags(BaseModel):
    joblisting_id: uuid.UUID = Field(alias="joblisting_id")
    tag_id: int = Field(alias="tag_id")

class PublicJobTagsInsert(TypedDict):
    joblisting_id: Annotated[uuid.UUID, Field(alias="joblisting_id")]
    tag_id: Annotated[int, Field(alias="tag_id")]

class PublicJobTagsUpdate(TypedDict):
    joblisting_id: NotRequired[Annotated[uuid.UUID, Field(alias="joblisting_id")]]
    tag_id: NotRequired[Annotated[int, Field(alias="tag_id")]]

class PublicKeyHighlights(BaseModel):
    created_at: datetime.datetime = Field(alias="created_at")
    highlight: str = Field(alias="highlight")
    id: uuid.UUID = Field(alias="id")
    report_id: uuid.UUID = Field(alias="report_id")

class PublicKeyHighlightsInsert(TypedDict):
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    highlight: Annotated[str, Field(alias="highlight")]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    report_id: Annotated[uuid.UUID, Field(alias="report_id")]

class PublicKeyHighlightsUpdate(TypedDict):
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    highlight: NotRequired[Annotated[str, Field(alias="highlight")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    report_id: NotRequired[Annotated[uuid.UUID, Field(alias="report_id")]]

class PublicParsedResume(BaseModel):
    created_at: datetime.datetime = Field(alias="created_at")
    id: uuid.UUID = Field(alias="id")
    parsed_resume: Json[Any] = Field(alias="parsed_resume")

class PublicParsedResumeInsert(TypedDict):
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    parsed_resume: Annotated[Json[Any], Field(alias="parsed_resume")]

class PublicParsedResumeUpdate(TypedDict):
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    parsed_resume: NotRequired[Annotated[Json[Any], Field(alias="parsed_resume")]]

class PublicScoredCandidates(BaseModel):
    created_at: datetime.datetime = Field(alias="created_at")
    id: uuid.UUID = Field(alias="id")
    score_data: Json[Any] = Field(alias="score_data")

class PublicScoredCandidatesInsert(TypedDict):
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    score_data: Annotated[Json[Any], Field(alias="score_data")]

class PublicScoredCandidatesUpdate(TypedDict):
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    score_data: NotRequired[Annotated[Json[Any], Field(alias="score_data")]]

class PublicSocialLinks(BaseModel):
    applicant_id: uuid.UUID = Field(alias="applicant_id")
    id: uuid.UUID = Field(alias="id")
    link: str = Field(alias="link")

class PublicSocialLinksInsert(TypedDict):
    applicant_id: Annotated[uuid.UUID, Field(alias="applicant_id")]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    link: Annotated[str, Field(alias="link")]

class PublicSocialLinksUpdate(TypedDict):
    applicant_id: NotRequired[Annotated[uuid.UUID, Field(alias="applicant_id")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    link: NotRequired[Annotated[str, Field(alias="link")]]

class PublicStaff(BaseModel):
    created_at: datetime.datetime = Field(alias="created_at")
    firebase_uid: str = Field(alias="firebase_uid")
    first_name: str = Field(alias="first_name")
    id: uuid.UUID = Field(alias="id")
    last_name: str = Field(alias="last_name")
    role: PublicUserRoles = Field(alias="role")

class PublicStaffInsert(TypedDict):
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    firebase_uid: Annotated[str, Field(alias="firebase_uid")]
    first_name: Annotated[str, Field(alias="first_name")]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    last_name: Annotated[str, Field(alias="last_name")]
    role: Annotated[PublicUserRoles, Field(alias="role")]

class PublicStaffUpdate(TypedDict):
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    firebase_uid: NotRequired[Annotated[str, Field(alias="firebase_uid")]]
    first_name: NotRequired[Annotated[str, Field(alias="first_name")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    last_name: NotRequired[Annotated[str, Field(alias="last_name")]]
    role: NotRequired[Annotated[PublicUserRoles, Field(alias="role")]]

class PublicTags(BaseModel):
    id: int = Field(alias="id")
    name: str = Field(alias="name")
    slug: Optional[str] = Field(alias="slug")

class PublicTagsInsert(TypedDict):
    id: NotRequired[Annotated[int, Field(alias="id")]]
    name: Annotated[str, Field(alias="name")]
    slug: NotRequired[Annotated[Optional[str], Field(alias="slug")]]

class PublicTagsUpdate(TypedDict):
    id: NotRequired[Annotated[int, Field(alias="id")]]
    name: NotRequired[Annotated[str, Field(alias="name")]]
    slug: NotRequired[Annotated[Optional[str], Field(alias="slug")]]

class PublicTranscribed(BaseModel):
    created_at: datetime.datetime = Field(alias="created_at")
    id: uuid.UUID = Field(alias="id")
    transcription: Json[Any] = Field(alias="transcription")

class PublicTranscribedInsert(TypedDict):
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    transcription: Annotated[Json[Any], Field(alias="transcription")]

class PublicTranscribedUpdate(TypedDict):
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    transcription: NotRequired[Annotated[Json[Any], Field(alias="transcription")]]

class PublicNotifications(BaseModel):
    body: Optional[str] = Field(alias="body")
    created_at: datetime.datetime = Field(alias="created_at")
    id: uuid.UUID = Field(alias="id")
    link: Optional[str] = Field(alias="link")
    read: bool = Field(alias="read")
    staff_id: uuid.UUID = Field(alias="staff_id")
    title: str = Field(alias="title")

class PublicNotificationsInsert(TypedDict):
    body: NotRequired[Annotated[Optional[str], Field(alias="body")]]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    link: NotRequired[Annotated[Optional[str], Field(alias="link")]]
    read: NotRequired[Annotated[bool, Field(alias="read")]]
    staff_id: Annotated[uuid.UUID, Field(alias="staff_id")]
    title: Annotated[str, Field(alias="title")]

class PublicNotificationsUpdate(TypedDict):
    body: NotRequired[Annotated[Optional[str], Field(alias="body")]]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    link: NotRequired[Annotated[Optional[str], Field(alias="link")]]
    read: NotRequired[Annotated[bool, Field(alias="read")]]
    staff_id: NotRequired[Annotated[uuid.UUID, Field(alias="staff_id")]]
    title: NotRequired[Annotated[str, Field(alias="title")]]

class PublicDailyActiveJobsLast7Days(BaseModel):
    date: Optional[datetime.date] = Field(alias="date")
    dow: Optional[int] = Field(alias="dow")
    jobs: Optional[int] = Field(alias="jobs")
    weekday: Optional[str] = Field(alias="weekday")

class PublicWeeklyApplicantsLast4Weeks(BaseModel):
    applicants: Optional[int] = Field(alias="applicants")
    iso_week: Optional[str] = Field(alias="iso_week")
    week_end: Optional[datetime.date] = Field(alias="week_end")
    week_start: Optional[datetime.date] = Field(alias="week_start")
