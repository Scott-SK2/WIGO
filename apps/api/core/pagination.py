from rest_framework.pagination import CursorPagination as DRFCursorPagination


class CursorPagination(DRFCursorPagination):
    """Pagination stable par curseur (§9.2 Conventions). L'ordre est fixé par chaque vue."""

    page_size = 20
    max_page_size = 50
    page_size_query_param = "page_size"
    ordering = "-created_at"
