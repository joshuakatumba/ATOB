from typing import Any

from supertokens_python import InputAppInfo, SupertokensConfig, init
from supertokens_python.ingredients.emaildelivery.types import (
    EmailDeliveryConfig,
    SMTPSettings,
    SMTPSettingsFrom,
)
from supertokens_python.recipe import emailpassword, emailverification, session, thirdparty
from supertokens_python.recipe.session import SessionContainer
from supertokens_python.recipe.thirdparty.interfaces import (
    APIInterface,
    APIOptions,
    SignInUpPostOkResult,
)
from supertokens_python.recipe.thirdparty.provider import Provider, RedirectUriInfo

from civis.config import Settings

_PROVIDERS: list[thirdparty.ProviderInput] = []


def _override_thirdparty_apis(original: APIInterface) -> APIInterface:
    original_sign_in_up_post = original.sign_in_up_post

    async def sign_in_up_post(
        provider: Provider,
        redirect_uri_info: RedirectUriInfo | None,
        oauth_tokens: dict[str, Any] | None,
        session: SessionContainer | None,
        should_try_linking_with_session_user: bool | None,
        tenant_id: str,
        api_options: APIOptions,
        user_context: dict[str, Any],
    ) -> Any:
        result = await original_sign_in_up_post(
            provider,
            redirect_uri_info,
            oauth_tokens,
            session,
            should_try_linking_with_session_user,
            tenant_id,
            api_options,
            user_context,
        )
        if isinstance(result, SignInUpPostOkResult):
            raw_id = result.raw_user_info_from_provider.from_id_token_payload or {}
            raw_info = result.raw_user_info_from_provider.from_user_info_api or {}
            name = raw_id.get("name") or raw_info.get("name")
            if isinstance(name, str) and name.strip():
                await result.session.merge_into_access_token_payload(
                    {"name": name.strip()[:200]}
                )
        return result

    original.sign_in_up_post = sign_in_up_post  # type: ignore[method-assign]
    return original


def configure_auth(settings: Settings) -> None:
    _PROVIDERS.clear()
    if settings.google_client_id and settings.google_client_secret:
        _PROVIDERS.append(
            thirdparty.ProviderInput(
                config=thirdparty.ProviderConfig(
                    third_party_id="google",
                    clients=[
                        thirdparty.ProviderClientConfig(
                            client_id=settings.google_client_id,
                            client_secret=settings.google_client_secret.get_secret_value(),
                            scope=["openid", "email", "profile"],
                        )
                    ],
                )
            )
        )
    smtp = SMTPSettings(
        host=settings.smtp_host,
        port=settings.smtp_port,
        from_=SMTPSettingsFrom("Civis", settings.smtp_from),
        secure=settings.environment == "production",
        username=settings.smtp_username,
        password=settings.smtp_password.get_secret_value() if settings.smtp_password else None,
    )
    init(
        app_info=InputAppInfo(
            app_name="Civis",
            api_domain=settings.api_domain,
            website_domain=settings.web_domain,
            api_base_path="/auth",
            website_base_path="/auth",
        ),
        supertokens_config=SupertokensConfig(
            connection_uri=settings.supertokens_uri,
            api_key=settings.supertokens_api_key.get_secret_value(),
        ),
        framework="fastapi",
        mode="asgi",
        telemetry=False,
        debug=False,
        recipe_list=[
            session.init(
                cookie_secure=settings.environment == "production",
                cookie_same_site="lax",
                anti_csrf="VIA_CUSTOM_HEADER",
            ),
            emailpassword.init(
                email_delivery=EmailDeliveryConfig(service=emailpassword.SMTPService(smtp))
            ),
            thirdparty.init(
                sign_in_and_up_feature=thirdparty.SignInAndUpFeature(providers=_PROVIDERS),
                override=thirdparty.InputOverrideConfig(apis=_override_thirdparty_apis),
            ),
            # /me remains available before verification, with zero allowance.
            emailverification.init(
                mode="OPTIONAL",
                email_delivery=EmailDeliveryConfig(service=emailverification.SMTPService(smtp)),
            ),
        ],
    )
