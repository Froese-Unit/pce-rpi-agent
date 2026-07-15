port module Main exposing (..)

import Api
import Browser
import Browser.Dom as Dom
import Browser.Navigation as Navigation
import Decode
import Dict
import Dropdown
import Element as El
import Element.Background as Background
import Element.Border as Border
import Element.Font as Font
import Element.Input as Input
import Encode
import Feedback
import Form
import Html exposing (Html)
import Html.Events
import Http
import Json.Decode as D
import Json.Encode as E
import Svg as S
import Svg.Attributes as SA
import Task
import Types exposing (..)
import Url
import Url.Parser as Parser
import Url.Parser.Query as Query
import Utils
import View



-- MAIN


main : Program () Model Msg
main =
    Browser.application
        { init = init
        , view = \model -> Browser.Document "PCE Webviz" [ View.view model ]
        , update = update
        , subscriptions = subscriptions
        , onUrlRequest = \_ -> NoOp
        , onUrlChange = \_ -> NoOp
        }



-- PORTS


port socketConnect : String -> Cmd msg


port sendMessage : String -> Cmd msg


port socketState : (Bool -> msg) -> Sub msg


port socketError : (String -> msg) -> Sub msg


port messageReceiver : (String -> msg) -> Sub msg



-- MODEL INIT


urlLang : Url.Url -> Maybe String
urlLang url =
    Parser.parse
        (Query.string "lang" |> Parser.query)
        url
        |> Maybe.withDefault Nothing


init : () -> Url.Url -> Navigation.Key -> ( Model, Cmd Msg )
init flags url key =
    let
        wsProtocol =
            if url.protocol == Url.Https then
                "wss"

            else
                "ws"

        wsPort =
            case url.port_ of
                Nothing ->
                    ""

                Just port_ ->
                    ":" ++ String.fromInt port_

        ( langSet, maybeGetTranslations ) =
            case urlLang url of
                Just lang ->
                    ( True, Api.getTranslations RecvTranslations lang )

                Nothing ->
                    ( False, Cmd.none )
    in
    ( initModel langSet
    , Cmd.batch
        [ socketConnect <| wsProtocol ++ "://" ++ url.host ++ wsPort ++ "/ws"
        , maybeGetTranslations
        ]
    )



-- UPDATE


update : Msg -> Model -> ( Model, Cmd Msg )
update msg model =
    case msg of
        NoOp ->
            ( model, Cmd.none )

        Errored string ->
            updateExp model <|
                \exp -> ( Error string, Cmd.none )

        RecvMeta (Ok meta) ->
            if model.meta.uuid /= "" && model.meta.uuid /= meta.uuid then
                err model <|
                    "Received new Meta with uuid "
                        ++ meta.uuid
                        ++ ", which differs from current uuid "
                        ++ model.meta.uuid

            else
                let
                    connection =
                        case model.exp of
                            Connecting ->
                                sendMessage <| Encode.uuidSocketMsg meta.uuid

                            Error _ ->
                                Cmd.none

                            Connected _ ->
                                Cmd.none

                    lang =
                        if model.langSet then
                            Cmd.none

                        else
                            Api.getTranslations RecvTranslations meta.lang
                in
                ( { model | meta = meta, langSet = True, slotForm = Form.empty () }
                , Cmd.batch [ connection, lang ]
                )

        RecvMeta (Err error) ->
            err model <| Utils.httpErrorToString error

        RecvTranslations (Ok translations) ->
            ( { model | translations = translations }
            , Cmd.none
            )

        RecvTranslations (Err error) ->
            err model <| Utils.httpErrorToString error

        SocketState (Ok open) ->
            updateExp model <|
                \exp ->
                    if open == True then
                        ( exp
                        , Api.getMeta RecvMeta
                        )

                    else
                        errExp "Socket unexpectedly closed"

        SocketState (Err error) ->
            err model error

        RecvSocketMsg result ->
            case result of
                Ok (SocketMsgError error) ->
                    ( { model | exp = Error error }, Cmd.none )

                Err error ->
                    ( { model | exp = Error <| D.errorToString error }, Cmd.none )

                Ok (SocketMsgPhase phase) ->
                    ( { model | exp = Connected phase }, Cmd.none )

                Ok (SocketMsgMeta meta) ->
                    ( { model | meta = meta }, Cmd.none )

                Ok (SocketMsgPlayers players) ->
                    ( { model | players = players }, Cmd.none )

        SelectSlot slot ->
            ( { model | slotForm = Form.send model.slotForm }
            , Api.postSlot RecvSlots slot
            )

        RecvSlots (Ok (GoodStatus slots)) ->
            let
                meta =
                    model.meta

                newMeta =
                    { meta | slots = slots }
            in
            ( { model | meta = newMeta, slotForm = Form.empty () }, Cmd.none )

        RecvSlots (Ok (BadStatus code feedback)) ->
            err model <|
                "RecvSlots errored with a "
                    ++ String.fromInt code
                    ++ " status code saying: "
                    ++ Feedback.getUnknown feedback

        RecvSlots (Err error) ->
            err model <| Utils.httpErrorToString error

        PidInput pid ->
            ( { model | pidForm = Form.input model.pidForm pid }
            , Cmd.none
            )

        SubmitPid ->
            ( { model | pidForm = Form.send model.pidForm }
            , Api.postPid RecvPids model.pidForm.input
            )

        RecvPids (Ok (GoodStatus pids)) ->
            let
                meta =
                    model.meta

                newMeta =
                    { meta | pids = pids }
            in
            ( { model | meta = newMeta, pidForm = Form.empty "" }, Cmd.none )

        RecvPids (Ok (BadStatus _ feedback)) ->
            ( { model | pidForm = Form.fail model.pidForm feedback }
            , Cmd.none
            )

        RecvPids (Err error) ->
            err model <| Utils.httpErrorToString error

        SubmitStartPhase ->
            ( { model | startPhaseForm = Form.send model.startPhaseForm }
            , Api.postStartPhase RecvPhase
            )

        RecvPhase (Ok (GoodStatus phase)) ->
            case model.exp of
                Connected _ ->
                    ( { model | exp = Connected phase, startPhaseForm = Form.empty () }
                    , Cmd.none
                    )

                _ ->
                    ( model, Cmd.none )

        RecvPhase (Ok (BadStatus code feedback)) ->
            err model <|
                "RecvPhase errored with a "
                    ++ String.fromInt code
                    ++ " status code saying: "
                    ++ Feedback.getUnknown feedback

        RecvPhase (Err error) ->
            err model <| Utils.httpErrorToString error

        SubmitReady ->
            ( { model | startPhaseForm = Form.send model.startPhaseForm }
            , Api.postReady RecvPlayers
            )

        RecvPlayers (Ok (GoodStatus players)) ->
            ( { model | players = players, startPhaseForm = Form.empty () }
            , Cmd.none
            )

        RecvPlayers (Ok (BadStatus code feedback)) ->
            err model <|
                "RecvPlayers errored with a "
                    ++ String.fromInt code
                    ++ " status code saying: "
                    ++ Feedback.getUnknown feedback

        RecvPlayers (Err error) ->
            err model <| Utils.httpErrorToString error

        PersonInputAge ageString ->
            let
                personInput =
                    model.personForm.input

                newAge =
                    case ( String.length ageString, String.toInt ageString ) of
                        ( 0, _ ) ->
                            Nothing

                        ( _, Nothing ) ->
                            personInput.age

                        ( _, Just age ) ->
                            Just age

                personForm =
                    { personInput | age = newAge }
                        |> Form.input model.personForm
            in
            ( { model | personForm = personForm }
            , Cmd.none
            )

        PersonSelectGender maybeGender ->
            let
                personInput =
                    model.personForm.input

                personForm =
                    { personInput | gender = maybeGender }
                        |> Form.input model.personForm
            in
            ( { model | personForm = personForm }
            , Cmd.none
            )

        PersonGenderDropdownMsg subMsg ->
            let
                ( state, cmd ) =
                    Dropdown.update (View.genderDropdownConfig model) subMsg model.personForm model.genderDropdown
            in
            ( { model | genderDropdown = state }
            , cmd
            )

        PersonSelectNationality maybeNationality ->
            let
                personInput =
                    model.personForm.input

                personForm =
                    { personInput | nationality = maybeNationality }
                        |> Form.input model.personForm
            in
            ( { model | personForm = personForm }
            , Cmd.none
            )

        PersonNationalityDropdownMsg subMsg ->
            let
                ( state, cmd ) =
                    Dropdown.update (View.nationalityDropdownConfig model) subMsg model.personForm model.nationalityDropdown
            in
            ( { model | nationalityDropdown = state }
            , cmd
            )

        SubmitPerson ->
            -- TODO: use Validate instead of manually doing this
            case validPerson model.personForm.input of
                Just person ->
                    ( { model | personForm = Form.send model.personForm }
                    , Api.postPerson RecvPersons person
                    )

                _ ->
                    ( model, Cmd.none )

        RecvPersons (Ok (GoodStatus qPreExperiment)) ->
            let
                ( exp, cmd ) =
                    case model.exp of
                        Connected (PreExperiment _ config pConfig) ->
                            ( Connected (PreExperiment qPreExperiment config pConfig)
                            , jumpToTop
                            )

                        _ ->
                            ( model.exp
                            , Cmd.none
                            )
            in
            ( { model | exp = exp, personForm = Form.empty initPerson }
            , cmd
            )

        RecvPersons (Ok (BadStatus _ feedback)) ->
            ( { model | personForm = Form.fail model.personForm feedback }
            , Cmd.none
            )

        RecvPersons (Err error) ->
            err model <| Utils.httpErrorToString error

        PersonalityInput questionId answer ->
            case Dict.get questionId (personalityQuestionsAll model) of
                Nothing ->
                    -- This should never happen
                    err model <| "Question id " ++ String.fromInt questionId ++ " is not found in personalityQuestionTexts"

                Just questionText ->
                    let
                        personalityForm =
                            model.personalityForm.input
                                |> Dict.insert questionId ( questionText, answer )
                                |> Form.input model.personalityForm
                    in
                    ( { model | personalityForm = personalityForm }
                    , Cmd.none
                    )

        SubmitPersonalityPre ->
            -- TODO: maybe recheck completion of questionnaire as done in view
            ( { model | personalityForm = Form.send model.personalityForm }
            , Api.postPersonalityPre RecvPersonalitiesPre model.personalityForm.input
            )

        RecvPersonalitiesPre (Ok (GoodStatus qPreExperiment)) ->
            let
                ( exp, cmd ) =
                    case model.exp of
                        Connected (PreExperiment _ config pConfig) ->
                            ( Connected (PreExperiment qPreExperiment config pConfig)
                            , jumpToTop
                            )

                        _ ->
                            ( model.exp
                            , Cmd.none
                            )
            in
            ( { model | exp = exp, personalityForm = Form.empty initPersonality }
            , cmd
            )

        RecvPersonalitiesPre (Ok (BadStatus _ feedback)) ->
            ( { model | personalityForm = Form.fail model.personalityForm feedback }
            , Cmd.none
            )

        RecvPersonalitiesPre (Err error) ->
            err model <| Utils.httpErrorToString error

        SubmitPersonalityAfter ->
            ( { model | personalityForm = Form.send model.personalityForm }
            , Api.postPersonalityAfter RecvPersonalitiesAfter model.personalityForm.input
            )

        RecvPersonalitiesAfter (Ok (GoodStatus qAfterExperiment)) ->
            let
                ( exp, cmd ) =
                    case model.exp of
                        Connected (AfterExperiment _ pConfig) ->
                            ( Connected (AfterExperiment qAfterExperiment pConfig)
                            , jumpToTop
                            )

                        _ ->
                            ( model.exp
                            , Cmd.none
                            )
            in
            ( { model | exp = exp, personalityForm = Form.empty initPersonality }
            , cmd
            )

        RecvPersonalitiesAfter (Ok (BadStatus _ feedback)) ->
            -- TODO: maybe recheck completion of questionnaire as done in view
            ( { model | personalityForm = Form.fail model.personalityForm feedback }
            , Cmd.none
            )

        RecvPersonalitiesAfter (Err error) ->
            err model <| Utils.httpErrorToString error

        ExperienceClickPresenceInput answer ->
            let
                experienceInput =
                    model.experienceForm.input

                experienceForm =
                    { experienceInput | clickPresence = Just answer }
                        |> Form.input model.experienceForm
            in
            ( { model | experienceForm = experienceForm }
            , Cmd.none
            )

        ExperienceClickConfidenceInput answer ->
            let
                experienceInput =
                    model.experienceForm.input

                experienceForm =
                    { experienceInput | clickConfidence = Just answer }
                        |> Form.input model.experienceForm
            in
            ( { model | experienceForm = experienceForm }
            , Cmd.none
            )

        ExperienceAbsenceFrequencyInput answer ->
            let
                experienceInput =
                    model.experienceForm.input

                maybeAbsenceStrength =
                    case answer of
                        0 ->
                            Nothing

                        _ ->
                            experienceInput.absenceStrength

                experienceForm =
                    { experienceInput | absenceFrequency = Just answer, absenceStrength = maybeAbsenceStrength }
                        |> Form.input model.experienceForm
            in
            ( { model | experienceForm = experienceForm }
            , Cmd.none
            )

        ExperienceAbsenceStrengthInput answer ->
            let
                experienceInput =
                    model.experienceForm.input

                experienceForm =
                    { experienceInput | absenceStrength = Just answer }
                        |> Form.input model.experienceForm
            in
            ( { model | experienceForm = experienceForm }
            , Cmd.none
            )

        SubmitExperience trialClick ->
            -- TODO: use Validate instead of manually doing this
            case validExperience trialClick model.experienceForm.input of
                Just experience ->
                    ( { model | experienceForm = Form.send model.experienceForm }
                    , Api.postExperience RecvExperiences experience
                    )

                _ ->
                    ( model, Cmd.none )

        RecvExperiences (Ok (GoodStatus qAfterTrial)) ->
            let
                ( exp, cmd ) =
                    case model.exp of
                        Connected (AfterTrial training nextPhase trialClicks _) ->
                            ( Connected (AfterTrial training nextPhase trialClicks qAfterTrial)
                            , jumpToTop
                            )

                        _ ->
                            ( model.exp
                            , Cmd.none
                            )
            in
            ( { model | exp = exp, experienceForm = Form.empty initExperience }
            , cmd
            )

        RecvExperiences (Ok (BadStatus _ feedback)) ->
            ( { model | experienceForm = Form.fail model.experienceForm feedback }
            , Cmd.none
            )

        RecvExperiences (Err error) ->
            err model <| Utils.httpErrorToString error

        PartnerTraitsInput trait answer ->
            let
                traitsInput =
                    model.traitsForm.input

                traitsForm =
                    traitsInput
                        |> setTrait trait (Just answer)
                        |> Form.input model.traitsForm
            in
            ( { model | traitsForm = traitsForm }
            , Cmd.none
            )

        SubmitPartnerTraits ->
            -- TODO: use Validate instead of manually doing this
            case validTraits model.traitsForm.input of
                Just traits ->
                    ( { model | traitsForm = Form.send model.traitsForm }
                    , Api.postPartnerTraits RecvPartnerTraits traits
                    )

                _ ->
                    ( model, Cmd.none )

        RecvPartnerTraits (Ok (GoodStatus qAfterExperiment)) ->
            let
                ( exp, cmd ) =
                    case model.exp of
                        Connected (AfterExperiment _ pConfig) ->
                            ( Connected (AfterExperiment qAfterExperiment pConfig)
                            , jumpToTop
                            )

                        _ ->
                            ( model.exp
                            , Cmd.none
                            )
            in
            ( { model | exp = exp, traitsForm = Form.empty initTraits }
            , cmd
            )

        RecvPartnerTraits (Ok (BadStatus _ feedback)) ->
            ( { model | traitsForm = Form.fail model.traitsForm feedback }
            , Cmd.none
            )

        RecvPartnerTraits (Err error) ->
            err model <| Utils.httpErrorToString error

        StrategySelfInput s ->
            let
                input =
                    model.strategyForm.input

                newForm =
                    Form.input model.strategyForm { input | self = s }
            in
            ( { model | strategyForm = newForm }
            , Cmd.none
            )

        StrategyOtherInput s ->
            let
                input =
                    model.strategyForm.input

                newForm =
                    Form.input model.strategyForm { input | other = s }
            in
            ( { model | strategyForm = newForm }
            , Cmd.none
            )

        StrategyCommentInput s ->
            let
                input =
                    model.strategyForm.input

                newForm =
                    Form.input model.strategyForm { input | comment = s }
            in
            ( { model | strategyForm = newForm }
            , Cmd.none
            )

        SubmitStrategy ->
            ( { model | strategyForm = Form.send model.strategyForm }
            , Api.postStrategy RecvStrategies model.strategyForm.input
            )

        RecvStrategies (Ok (GoodStatus qAfterExperiment)) ->
            let
                ( exp, cmd ) =
                    case model.exp of
                        Connected (AfterExperiment _ pConfig) ->
                            ( Connected (AfterExperiment qAfterExperiment pConfig)
                            , jumpToTop
                            )

                        _ ->
                            ( model.exp
                            , Cmd.none
                            )
            in
            ( { model | exp = exp, strategyForm = Form.empty initStrategy }
            , cmd
            )

        RecvStrategies (Ok (BadStatus _ feedback)) ->
            ( { model | strategyForm = Form.fail model.strategyForm feedback }
            , Cmd.none
            )

        RecvStrategies (Err error) ->
            err model <| Utils.httpErrorToString error


updateExp : Model -> (Exp -> ( Exp, Cmd Msg )) -> ( Model, Cmd Msg )
updateExp model func =
    let
        ( newExp, cmd ) =
            func model.exp
    in
    ( { model | exp = newExp }, cmd )


err : Model -> String -> ( Model, Cmd Msg )
err model text =
    ( { model | exp = Error text }, Cmd.none )


errExp : String -> ( Exp, Cmd Msg )
errExp text =
    ( Error text, Cmd.none )


jumpToTop : Cmd Msg
jumpToTop =
    Task.perform (\_ -> NoOp) (Dom.setViewport 0 0)



-- SUBSCRIPTIONS


subscriptions : Model -> Sub Msg
subscriptions _ =
    Sub.batch
        [ messageReceiver (RecvSocketMsg << D.decodeString Decode.socketMsg)
        , socketState (SocketState << Ok)
        , socketError (SocketState << Err)
        ]
