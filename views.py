from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .models import Choice, Course, Enrollment, Learner, Submission


def extract_answers(request, course):
    """Return selected choices that belong to the requested course."""
    selected_ids = []

    for key, value in request.POST.items():
        if key.startswith("choice"):
            try:
                selected_ids.append(int(value))
            except (TypeError, ValueError):
                continue

    return Choice.objects.filter(
        id__in=selected_ids,
        question__course=course,
    )


@login_required
@require_POST
def submit(request, course_id):
    """Save the learner's selected choices and redirect to the exam result."""
    course = get_object_or_404(Course, pk=course_id)

    # This demo project's Learner model is linked to Django users by email.
    learner = Learner.objects.filter(email=request.user.email).first()
    if learner is None:
        return HttpResponseForbidden(
            "Your account is not linked to a learner record. Contact the course administrator."
        )

    enrollment = get_object_or_404(
        Enrollment,
        learner=learner,
        course=course,
    )

    submission = Submission.objects.create(enrollment=enrollment)
    submission.choices.set(extract_answers(request, course))

    return HttpResponseRedirect(
        reverse(
            "onlinecourse:exam_result",
            args=(course.id, submission.id),
        )
    )


@login_required
def show_exam_result(request, course_id, submission_id):
    """Calculate and display the score for a learner's submitted exam."""
    course = get_object_or_404(Course, pk=course_id)

    learner = Learner.objects.filter(email=request.user.email).first()
    if learner is None:
        return HttpResponseForbidden(
            "Your account is not linked to a learner record. Contact the course administrator."
        )

    submission = get_object_or_404(
        Submission,
        pk=submission_id,
        enrollment__learner=learner,
        enrollment__course=course,
    )

    selected_choices = submission.choices.select_related("question")
    total_score = 0

    for question in course.question_set.prefetch_related("choice_set"):
        selected_ids = selected_choices.filter(
            question=question
        ).values_list("id", flat=True)
        if question.is_get_score(selected_ids):
            total_score += question.grade

    context = {
        "course": course,
        "grade": total_score,
        "choices": selected_choices,
    }
    return render(request, "onlinecourse/exam_result_bootstrap.html", context)
