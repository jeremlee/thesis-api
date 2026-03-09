from entities.fastapi.schema_public_latest import (
    PublicTags,
    PublicJobTags,
    PublicJobListings,
    PublicJlRequirements,
)


class JobTags_Tags(PublicJobTags):
    tags: PublicTags


class JobListingWithRelations(PublicJobListings):
    jl_requirements: list[PublicJlRequirements]
    job_tags: list[JobTags_Tags]
