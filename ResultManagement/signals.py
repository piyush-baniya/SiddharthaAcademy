# ResultManagement/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import StudentResult, StudentOverallResult

@receiver(post_save, sender=StudentResult)
def update_overall_result_on_save(sender, instance, created, **kwargs):
    """Update overall result when a student result is saved"""
    try:
        overall_result, created = StudentOverallResult.objects.get_or_create(
            examination=instance.examination,
            student=instance.student
        )
        overall_result.calculate_overall_result()
    except Exception as e:
        # Log the error but don't fail the save operation
        print(f"Error updating overall result: {e}")

@receiver(post_delete, sender=StudentResult)
def update_overall_result_on_delete(sender, instance, **kwargs):
    """Update overall result when a student result is deleted"""
    try:
        overall_result = StudentOverallResult.objects.filter(
            examination=instance.examination,
            student=instance.student
        ).first()
        
        if overall_result:
            # Check if there are any remaining results for this student in this exam
            remaining_results = StudentResult.objects.filter(
                examination=instance.examination,
                student=instance.student
            ).exists()
            
            if remaining_results:
                overall_result.calculate_overall_result()
            else:
                # No results left, delete the overall result
                overall_result.delete()
    except Exception as e:
        # Log the error but don't fail the delete operation
        print(f"Error updating overall result on delete: {e}")