from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    """Object-level check for models that expose an `owner` chain back to a user.

    Every model in this project can resolve its owning user, either directly
    (`Goal.user`) or through its parents (`Task -> Milestone -> Goal -> user`).
    Models implement `owner_user_id` for that purpose.
    """

    def has_object_permission(self, request, view, obj):
        owner_id = getattr(obj, "owner_user_id", None)
        return owner_id is not None and owner_id == request.user.id
