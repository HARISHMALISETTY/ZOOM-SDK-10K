from django.core.management.base import BaseCommand
from meetings.utils import check_upcoming_meetings

class Command(BaseCommand):
    help = 'Check for upcoming meetings and send reminders'

    def handle(self, *args, **options):
        self.stdout.write('Checking for upcoming meetings...')
        check_upcoming_meetings()
        self.stdout.write(self.style.SUCCESS('Successfully checked meetings and sent reminders')) 