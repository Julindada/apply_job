from dataclasses import dataclass, field


@dataclass
class CompanyAddress:
    type: str | None = None
    street_address: str | None = None
    address_locality: str | None = None
    address_region: str | None = None
    postal_code: str | None = None
    address_country: str | None = None


@dataclass
class LinkedInJobDto:
    """LinkedIn 职位数据模型。"""

    id: str = ""
    tracking_id: str | None = None
    ref_id: str | None = None
    link: str | None = None
    title: str | None = None
    company_name: str | None = None
    company_linkedin_url: str | None = None
    company_logo: str | None = None
    location: str | None = None
    posted_at: str | None = None
    benefits: list[str] = field(default_factory=list)
    description_html: str | None = None
    applicants_count: str | None = None
    apply_url: str | None = None
    salary: str | None = None
    description_text: str | None = None
    seniority_level: str | None = None
    employment_type: str | None = None
    job_function: str | None = None
    industries: str | None = None
    input_url: str | None = None
    company_address: CompanyAddress | None = None
    company_website: str | None = None
    company_slogan: str | None = None
    company_description: str | None = None
    company_employees_count: int | None = None
