from rest_framework import serializers

from .models import MemberRole, Organization, OrganizationMember, OwnershipClaim


class OrganizationPublicSerializer(serializers.ModelSerializer):
    """Profil public (SCR-07) : badge vérifié, revendicable."""

    verified = serializers.BooleanField(source="is_verified", read_only=True)
    logo = serializers.ImageField(read_only=True)

    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "slug",
            "type",
            "description",
            "logo",
            "website",
            "verified",
            "is_claimable",
        ]


class OrganizationWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["name", "type", "description", "website", "contact_email", "bce_number"]


class OrganizationPrivateSerializer(OrganizationPublicSerializer):
    role = serializers.SerializerMethodField()
    members = serializers.SerializerMethodField()

    class Meta(OrganizationPublicSerializer.Meta):
        fields = OrganizationPublicSerializer.Meta.fields + [
            "contact_email",
            "bce_number",
            "verification_status",
            "trust_level",
            "role",
            "members",
        ]

    def get_role(self, org) -> str | None:
        return org.role_of(self.context["request"].user)

    def get_members(self, org) -> list[dict]:
        return [
            {"email": m.user.email, "name": m.user.public_name, "role": m.role}
            for m in org.members.select_related("user")
        ]


class MemberSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=MemberRole.choices, default=MemberRole.EDITOR)


class ClaimSerializer(serializers.ModelSerializer):
    class Meta:
        model = OwnershipClaim
        fields = ["id", "evidence", "status", "created_at"]
        read_only_fields = ["id", "status", "created_at"]


class OrganizationMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationMember
        fields = ["user", "role"]
