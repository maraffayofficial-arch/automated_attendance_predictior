"""
Role-based access control middleware for Flask routes.
Protects endpoints based on user roles (admin, teacher, viewer).
"""

from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt
from functools import wraps


def role_required(*allowed_roles):
    """
    Decorator to restrict route access based on user roles.

    Usage:
        @role_required('admin')
        @role_required('admin', 'teacher')

    Args:
        allowed_roles: Tuple of role names that can access this route

    Returns:
        Decorator function
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            user_role = claims.get('role', 'viewer')

            if user_role not in allowed_roles:
                return jsonify({
                    'error': 'Access denied',
                    'message': f'This action requires one of these roles: {", ".join(allowed_roles)}',
                    'your_role': user_role
                }), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator


def admin_required(fn):
    """Shortcut decorator for admin-only routes."""
    return role_required('admin')(fn)


def admin_or_teacher_required(fn):
    """Shortcut decorator for admin or teacher routes."""
    return role_required('admin', 'teacher')(fn)


def get_user_role():
    """
    Get the current user's role from JWT token.
    Must be called within a JWT-protected route.

    Returns:
        str: User role ('admin', 'teacher', 'viewer')
    """
    try:
        verify_jwt_in_request()
        claims = get_jwt()
        return claims.get('role', 'viewer')
    except:
        return None


def get_user_department():
    """
    Get the current user's department from JWT token.
    Must be called within a JWT-protected route.

    Returns:
        str: User department or None
    """
    try:
        verify_jwt_in_request()
        claims = get_jwt()
        return claims.get('department')
    except:
        return None


def get_user_person_id():
    """
    Get the current user's person_id from JWT token.
    Must be called within a JWT-protected route.

    Returns:
        str: User person_id or None
    """
    try:
        verify_jwt_in_request()
        claims = get_jwt()
        return claims.get('person_id')
    except:
        return None


def can_access_all_departments():
    """
    Check if current user can access all departments.
    Only admins can see all departments.

    Returns:
        bool: True if user is admin, False otherwise
    """
    role = get_user_role()
    return role == 'admin'
