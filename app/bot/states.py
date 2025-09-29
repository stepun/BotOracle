"""
FSM States for Bot Oracle onboarding questionnaire
"""
from aiogram.fsm.state import State, StatesGroup

class OnboardingStates(StatesGroup):
    """States for user onboarding questionnaire"""
    waiting_for_age = State()
    waiting_for_gender = State()
    completed = State()