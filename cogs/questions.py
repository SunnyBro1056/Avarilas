import discord
import string
from discord import app_commands
from discord.ext import commands
from pathlib import Path
from typing import Any
import random
import json

class Prompter(commands.Cog):
    """This class regisers the 'exam' and 'question' slash commands.
    It also immediately loads the questions.json and tests.json file on
    initiation."""

############################
# INITIALIZATION FUNCTIONS #
############################

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.questions: dict[str, dict[str, str | list[tuple[str, bool]]]] = {}
        self.tests: dict[str, dict[str, list[str]]] = {}
        BASE_DIR = Path(__file__).resolve().parent.parent
        self.questions_file = BASE_DIR / "data" / "questions.json"
        self.tests_file = BASE_DIR / "data" / "tests.json"

        self.load_tests()
        self.load_questions()

    def load_questions(self):        
        try:
            with open(self.questions_file, "r") as f:
                self.questions = json.load(f)
        except:
            self.questions = {}

    def load_tests(self):
        try:
            with open(self.tests_file, "r") as f:
                self.tests = json.load(f)
        except:
            self.tests = {}

#######################
# GET RANDOM QUESTION #
#######################

    async def get_question(self, subject: str, chapter: str | None) -> tuple[Question | None, str | None]:
        """This function chooses a random question from a given subject
        and returns a Question object with shuffled answers. If any problems
        arise, the function passes an error message string."""
        answers: list[tuple[str, bool]]

        # Ensure user entered a valid subject
        if subject not in self.tests:
            return None, "Subject not found."
        current_test = self.tests[subject]
       
        # If user did not specify a chapter, use a random one
        if chapter is None:
            # This collects only chapters with questions in them
            valid_chapters = [
                chapter for chapter, questions in current_test.items()
                if questions
            ]
            if not valid_chapters:
                return None, "No chapters with questions."
            # Choose a chapter, then choose a random question from that chapter
            chapter = random.choice(valid_chapters)

        # If user entered a chapter, validate it.
        else:
            if chapter not in current_test:
                return None, "Chapter not found."
            if not current_test[chapter]:
                return None, "Chapter has no valid questions."

        # Pick a random question from the subject - chapter and ensure it exists in the questions file
        question = random.choice(current_test[chapter])
        if question not in self.questions:
            return None, "Question UUID missing"

        # Turn the list of answers into a list of ("prompt", bool) tuples and shuffle them
        current = self.questions[question]
        answers_raw = list(current["answers"])
        answers = [(str(a), bool(b)) for a, b in answers_raw]
        random.shuffle(answers)

        # Build the Question object
        question_obj = Question(
            str(current['question']),
            str(current['questionType']),
            answers,
            str(current['explanation'])
        )

        return question_obj, None

################
# EXAM COMMAND #
################

    @app_commands.command(name="exam", description="Receive a fixed number of questions")
    @app_commands.describe(subject="Choose a subject", chapter="Optional chapter filter", number="The amount of questions")
    async def exam(
        self,
        interaction: discord.Interaction,
        subject: str,
        number: int,
        chapter: str | None = None
    ):
        """This function holds the '/exam' command. It takes a subject and a number of questions for the
        user, and continues to ask the user questions after they answer the previous question."""
        question_obj: Question
        msg: Any # Typecasting got too hard so I gave up

        # This is an artificial constraint to prevent bot abuse, can be changed with zero issues
        if not 0 < number < 30:
            await interaction.response.send_message("Only a maximum of 30 questions in a row are supported.")
            return
        
        # TODO: separate logic in get_questions function so we can validate if a subject has chapters
        # or if a chapter has questions. The way this is right now, it sends two messages before it errors
        # out and is kind of janky.

        # Loops so that user can answer questions without typing the command every time
        await interaction.response.send_message(f"Starting an exam with {number} questions..")
        for _ in range(number):

            # Get a random question with error handling
            result, error = await self.get_question(subject, chapter)
            if error or result is None:
                await interaction.followup.send(error or "Unknown error")
                return
            question_obj = result

            # Build the initial embed for the question
            embed = discord.Embed(
                color = discord.Color.blue(),
                title = f"Question: {subject} {chapter if chapter else ""}",
                description = (
                    f"{question_obj.prompt}\n\n"
                    + "\n".join(
                            f"**{string.ascii_uppercase[i]}**. {choice_text}"
                            for i, (choice_text, _) in enumerate(question_obj.answers)
                        )
                )
            )
            # Build the View object (the buttons)
            view = QuizView(question_obj.answers)

            # Send the message
            msg = await interaction.followup.send(embed=embed, view=view)

            # Waits until user presses a button to continue running
            await view.wait()

            # Update the embed with the result
            if view.user_correct:
                embed_color = discord.Color.green()
                emote = '✅ '
            else:
                embed_color = discord.Color.red()
                emote = '❌'

            # Build the new embed
            new_embed = discord.Embed(
                color = embed_color,
                title = f"Question: {subject} {chapter if chapter else ""}",
                description = (
                    f"{question_obj.prompt}\n\n"
                    + "\n".join(
                            f"**{string.ascii_uppercase[i]}**. {choice_text}"
                            for i, (choice_text, _) in enumerate(question_obj.answers)
                        )
                    + f"\n\n {emote} **Explanation:** {question_obj.explanation}" 
                )
            )
            await msg.edit(embed=new_embed, view=None)
            # The for loop will restart now for 'number' times to keep asking questions

####################
# QUESTION COMMAND #
####################

    @app_commands.command(name="question", description="A test question command")
    @app_commands.describe(subject="Choose a subject", chapter="Optional chapter filter")
    async def question(
        self, 
        interaction: discord.Interaction, 
        subject: str, 
        chapter: str | None = None
    ):
        """This is the main 'question' command which searches a test
        in the self.tests memory for a specific test. Each test holds
        chapters, and those chapters hold reference UUIDs to specific
        questions."""

        # Pick a random question with error handling
        result, error = await self.get_question(subject, chapter)       
        if error or result is None:
            await interaction.response.send_message(error)
            return
        question_obj = result

        # Build the initial embed for the question
        embed = discord.Embed(
            color = discord.Color.blue(),
            title = f"Question: {subject} {chapter if chapter else ""}",
            description = (
                f"{question_obj.prompt}\n\n"
                + "\n".join(
                        f"**{string.ascii_uppercase[i]}**. {choice_text}"
                        for i, (choice_text, _) in enumerate(question_obj.answers)
                    )
            )
        )
        
        # Create the View object for the message (the buttons)
        view = QuizView(question_obj.answers)
        await interaction.response.send_message(embed=embed, view=view)

        # Waits until user presses a button to continue running
        await view.wait()

        # Update the embed with the result
        if view.user_correct:
            embed_color = discord.Color.green()
            emote = '✅ '
        else:
            embed_color = discord.Color.red()
            emote = '❌'

        # Build the new embed
        new_embed = discord.Embed(
            color = embed_color,
            title = f"Question: {subject} {chapter if chapter else ""}",
            description = (
                f"{question_obj.prompt}\n\n"
                + "\n".join(
                        f"**{string.ascii_uppercase[i]}**. {choice_text}"
                        for i, (choice_text, _) in enumerate(question_obj.answers)
                    )
                + f"\n\n {emote} **Explanation:** {question_obj.explanation}" 
            )
        )
        await interaction.edit_original_response(embed=new_embed, view=None)

    @question.autocomplete('subject')
    @exam.autocomplete('subject')
    async def subject_autocomplete(
        self,
        _: discord.Interaction,
        current: str
    ) -> list[app_commands.Choice[str]]:
        """This function is an autocomplete helper for the 'question' 
        and 'exam' commands. It searches the currently added exams and 
        presents the user with options."""

        return [
            app_commands.Choice(name=subject, value=subject)
            for subject in self.tests if current.lower() in subject.lower()
        ]

    @question.autocomplete('chapter')
    @exam.autocomplete('chapter')
    async def chapter_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> list[app_commands.Choice[str]]:

        subject = getattr(interaction.namespace, "subject", None)

        if not subject or subject not in self.tests:
            return []

        chapters = self.tests[subject].keys()

        return [
            app_commands.Choice(name=chapter, value=chapter)
            for chapter in chapters if current.lower() in chapter.lower()
        ]

##################
# HELPER CLASSES #
##################

class Question():
    """This class acts as a namespace for a given question so it can be easily
    referenced."""
    def __init__(self, prompt: str, type: str, answers: list[tuple[str, bool]] , explanation: str):
        self.prompt = prompt
        self.type = type
        self.answers = answers
        self.explanation = explanation


class QuizView(discord.ui.View):
    """This class builds 4 multiple choice buttons for a question
    and assigns them with alphabetical labels."""
    def __init__(self, answers: list[tuple[str, bool]]):
        super().__init__()
        labels = ["A", "B", "C", "D"]
        self.user_answered = False
        self.user_correct = False

        # Assigns answers to buttons in format (A, ("answer", bool))
        for label, (text, is_correct) in zip(labels, answers):
            self.add_item(QuizButton(label, text, is_correct, self))

class QuizButton(discord.ui.Button[QuizView]):
    """This class builds each individual button and can edit the View object's attributes
    when clicked."""
    def __init__(self, label: str, answer: str, is_correct: bool, view: QuizView):
        super().__init__(
            label=label,
            style=discord.ButtonStyle.primary
        )
        self.answer = answer
        self.is_correct = is_correct
        self.view_ref = view

    async def callback(self, interaction: discord.Interaction):
        if self.is_correct:
            self.view_ref.user_correct = True
        else:
            self.view_ref.user_correct = False
        
        self.view_ref.stop()
        self.view_ref.user_answered = True

async def setup(bot: commands.Bot):
    """This is the function that actually registers the Prompter class as a cog"""
    await bot.add_cog(Prompter(bot))
