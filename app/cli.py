import click

from . import db
from .models import User


def register_cli(app):
    @app.cli.command("make-admin")
    @click.argument("email")
    def make_admin(email):
        """Give the user with this email the admin role."""
        user = User.query.filter_by(email=email.strip().lower()).first()
        if not user:
            click.echo("No user with that email.")
            return
        user.role = "admin"
        db.session.commit()
        click.echo(f"{user.email} is now an admin.")
