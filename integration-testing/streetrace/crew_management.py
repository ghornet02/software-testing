"""Crew management module for StreetRace Manager."""

from __future__ import annotations

from dataclasses import dataclass

from .registration import CrewMember, RegistrationModule


@dataclass(frozen=True)
class CrewSkill:
    """A named skill and its level (1-10) for a crew member."""

    name: str
    level: int


class CrewManagementError(ValueError):
    """Raised when a crew-management operation is invalid."""


class CrewManagementModule:
    """Manages role assignments and skill levels for registered crew members."""

    def __init__(self, registration: RegistrationModule) -> None:
        self._registration = registration
        self._roles: dict[str, str] = {}
        self._skills: dict[str, dict[str, int]] = {}

    def assign_role(self, member_name: str, role: str) -> str:
        """Assign a role to a registered member.

        The assigned role overrides the role given at registration.

        Returns:
            The cleaned role name.

        Raises:
            CrewManagementError: If the member is unknown or the role is empty.
        """
        key = self._validate_registered_member(member_name)
        cleaned_role = role.strip() if isinstance(role, str) else ""
        if not cleaned_role:
            raise CrewManagementError("Role is required.")

        registered_member = self._registration.get_member(member_name)
        previous_assigned = self._roles.get(key)
        self._roles[key] = cleaned_role

        if (
            previous_assigned is not None
            and previous_assigned.casefold() == registered_member.role.casefold()
            and cleaned_role.casefold() != registered_member.role.casefold()
        ):
            self._registration._members[key] = CrewMember(name=registered_member.name, role=cleaned_role)

        return cleaned_role

    def get_role(self, member_name: str) -> str:
        """Return the member's assigned role, falling back to their registration role."""
        key = self._validate_registered_member(member_name)
        if key in self._roles:
            return self._roles[key]
        return self._registration.get_member(member_name).role

    def set_skill(self, member_name: str, skill_name: str, level: int) -> CrewSkill:
        """Record a skill level for a member.

        Args:
            member_name: Registered member.
            skill_name: Skill name, stored case-insensitively.
            level: Integer from 1 to 10.

        Raises:
            CrewManagementError: If the member is unknown or the input is invalid.
        """
        key = self._validate_registered_member(member_name)
        cleaned_skill = skill_name.strip() if isinstance(skill_name, str) else ""
        if not cleaned_skill:
            raise CrewManagementError("Skill name is required.")
        if not isinstance(level, int) or not 1 <= level <= 10:
            raise CrewManagementError("Skill level must be an integer between 1 and 10.")

        member_skills = self._skills.setdefault(key, {})
        member_skills[cleaned_skill.casefold()] = level
        return CrewSkill(name=cleaned_skill, level=level)

    def get_skill_level(self, member_name: str, skill_name: str) -> int:
        """Return the recorded level of a skill for a member.

        Raises:
            CrewManagementError: If the member is unknown or the skill is not recorded.
        """
        key = self._validate_registered_member(member_name)
        cleaned_skill = skill_name.strip() if isinstance(skill_name, str) else ""
        if not cleaned_skill:
            raise CrewManagementError("Skill name is required.")

        member_skills = self._skills.get(key, {})
        skill_level = member_skills.get(cleaned_skill.casefold())
        if skill_level is None:
            raise CrewManagementError(
                f"Skill '{cleaned_skill}' is not recorded for member '{member_name.strip()}'."
            )
        return skill_level

    def list_member_skills(self, member_name: str) -> list[CrewSkill]:
        """Return a member's skills sorted by name."""
        key = self._validate_registered_member(member_name)
        member_skills = self._skills.get(key, {})
        return [
            CrewSkill(name=skill_name, level=member_skills[skill_name])
            for skill_name in sorted(member_skills.keys())
        ]

    def _validate_registered_member(self, member_name: str) -> str:
        """Validate that a member is registered and return their lookup key."""
        cleaned_name = member_name.strip() if isinstance(member_name, str) else ""
        if not cleaned_name:
            raise CrewManagementError("Member name is required.")
        if not self._registration.is_registered(cleaned_name):
            raise CrewManagementError(f"Crew member '{cleaned_name}' is not registered.")
        return cleaned_name.casefold()
