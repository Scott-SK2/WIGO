from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class AuthThrottle(AnonRateThrottle):
    scope = "auth"


class NewsletterThrottle(AnonRateThrottle):
    scope = "newsletter"


class ReportThrottle(UserRateThrottle):
    scope = "report"


class AnonReportThrottle(AnonRateThrottle):
    scope = "report"


class SubmitThrottle(UserRateThrottle):
    scope = "submit"
