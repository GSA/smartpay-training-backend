import logging
from training.repositories import GspcCompletionRepository, UserRepository, GspcInviteRepository
from training.schemas import GspcSubmission, GspcResult, GspcCompletion
from sqlalchemy.orm import Session
from training.services import Certificate
from string import Template
from email.message import EmailMessage
from smtplib import SMTP
from training.errors import SendEmailError
from training.config import settings

CERTIFICATE_EMAIL_TEMPLATE = Template('''
    <p>Hello $name,</p>

    <p>
    Congratulations!
    </p>
    <p>You've successfully met the GSPC requirements.</p>
    <p>Your certificate is attached below.</p>
    <p>
    If you did not submit this request, you may be receiving this message in error. Please disregard this email. If you have any questions or need further
    assistance, email us at <a href="mailto:smartpaygspc@gsa.gov">smartpaygspc@gsa.com</a>.
    </p>
    <p>Thank you.</p>
    ''')


class GspcService():
    def __init__(self, db: Session):
        self.gspc_completion_repo = GspcCompletionRepository(db)
        self.gspc_invite_repo = GspcInviteRepository(db)
        self.user_repo = UserRepository(db)
        self.certificate_service = Certificate()

    def grade(self, user_id: int, submission: GspcSubmission) -> GspcResult:
        """
        Grades a GspcSubmission submitted by user. Sends congratulation email if user meets the criteria.
        :param user_id: User ID
        :param submission: Quiz submission object
        :return: GspcResult model which includes the final result
        """

        gspc_invite = self.gspc_invite_repo.get_by_gspc_invite_id(submission.gspc_invite_id)

        passed = all(question.correct for question in submission.responses.responses)

        responses_dict = submission.responses.model_dump()
        result = self.gspc_completion_repo.create(GspcCompletion(
            user_id=user_id,
            passed=passed,
            certification_expiration_date=gspc_invite.certification_expiration_date,
            responses=responses_dict,
            gspc_invite_id=gspc_invite.gspc_invite_id
        ))

        if (passed):
            try:
                user = self.user_repo.find_by_id(user_id)
                pdf_bytes = self.certificate_service.generate_gspc_pdf(
                    user.name,
                    user.agency.name,
                    result.submit_ts,
                    result.certification_expiration_date
                )

                self.email_certificate(user.name, user.email, pdf_bytes)
                logging.info(f"Sent confirmation email to {user.email} for passing training quiz")

                self.gspc_invite_repo.set_completion_date(gspc_invite.id)
            except Exception as e:
                logging.error("Error sending quiz confirmation mail", e)
                raise

        result = GspcResult(
            passed=passed,
            cert_id=result.id
        )

        return result

    def email_certificate(self, user_name: str, to_email: str, certificate: bytes) -> None:
        """
        Sends congratulatory email to user with certificate attached.
        :param user_name: User's Name
        :param to_email: User's email
        :param certificate: Certificate PDF file
        :return: N/A
        """
        body = CERTIFICATE_EMAIL_TEMPLATE.substitute({"name": user_name})
        message = EmailMessage()
        message.set_content(body, subtype="html")
        message["Subject"] = "Certificate – GSA SmartPay® Program Certificate"
        message["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
        message["To"] = to_email
        message.add_attachment(certificate, maintype="application", subtype="pdf", filename="GSPC Certificate.pdf")

        with SMTP(settings.SMTP_SERVER, port=settings.SMTP_PORT) as smtp:
            smtp.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                smtp.login(user=settings.SMTP_USER, password=settings.SMTP_PASSWORD)
            try:
                smtp.send_message(message)
            except Exception as e:
                raise SendEmailError from e
            finally:
                smtp.quit()
