module Api exposing
    ( getMeta
    , getTranslations
    , postExperience
    , postPartnerTraits
    , postPerson
    , postPersonalityAfter
    , postPersonalityPre
    , postPid
    , postReady
    , postSlot
    , postStartPhase
    , postStrategy
    )

import Decode
import Encode
import Feedback
import Http
import HttpBuilder
import I18Next exposing (Translations, translationsDecoder)
import Json.Decode as D
import Json.Encode as E
import Task exposing (Task)
import Types exposing (..)


getMeta : (Result Http.Error Meta -> Msg) -> Cmd Msg
getMeta toMsg =
    builder
        { method = HttpBuilder.get
        , path = "/meta"
        , expect = Http.expectJson toMsg Decode.meta
        }
        |> HttpBuilder.request


getTranslations : (Result Http.Error Translations -> Msg) -> String -> Cmd Msg
getTranslations toMsg lang =
    builderRoot
        { method = HttpBuilder.get
        , path = "/assets/translations/" ++ lang ++ ".json"
        , expect = Http.expectJson toMsg <| translationsDecoder
        }
        |> HttpBuilder.request


postSlot : (Result Http.Error (ApiResponse Slots) -> Msg) -> Slot -> Cmd Msg
postSlot toMsg slot =
    builder
        { method = HttpBuilder.post
        , path = "/meta/slot"
        , expect = expectJson toMsg (D.field "slots" Decode.slots) []
        }
        |> HttpBuilder.withJsonBody (Encode.slot slot)
        |> HttpBuilder.request


postPid : (Result Http.Error (ApiResponse Pids) -> Msg) -> String -> Cmd Msg
postPid toMsg pid =
    builder
        { method = HttpBuilder.post
        , path = "/meta/pid"
        , expect = expectJson toMsg (D.field "pids" Decode.pids) [ ( "pid", "pid" ) ]
        }
        |> HttpBuilder.withJsonBody (Encode.pid pid)
        |> HttpBuilder.request


postReady : (Result Http.Error (ApiResponse Players) -> Msg) -> Cmd Msg
postReady toMsg =
    builder
        { method = HttpBuilder.post
        , path = "/players/ready"
        , expect = expectJson toMsg (D.field "players" Decode.players) []
        }
        |> HttpBuilder.request


postStartPhase : (Result Http.Error (ApiResponse Phase) -> Msg) -> Cmd Msg
postStartPhase toMsg =
    builder
        { method = HttpBuilder.post
        , path = "/phase/start"
        , expect = expectJson toMsg (D.field "phase" Decode.phase) []
        }
        |> HttpBuilder.request


postPerson : (Result Http.Error (ApiResponse QPreExperiment) -> Msg) -> ValidPerson -> Cmd Msg
postPerson toMsg person =
    builder
        { method = HttpBuilder.post
        , path = "/phase/questionnaire"
        , expect = expectJson toMsg (D.field "questionnaires" Decode.qPreExperiment) []
        }
        |> HttpBuilder.withJsonBody (Encode.person person)
        |> HttpBuilder.request


postPersonalityPre : (Result Http.Error (ApiResponse QPreExperiment) -> Msg) -> Personality -> Cmd Msg
postPersonalityPre toMsg personality =
    builder
        { method = HttpBuilder.post
        , path = "/phase/questionnaire"
        , expect = expectJson toMsg (D.field "questionnaires" Decode.qPreExperiment) []
        }
        |> HttpBuilder.withJsonBody (Encode.personalityPre personality)
        |> HttpBuilder.request


postPersonalityAfter : (Result Http.Error (ApiResponse QAfterExperiment) -> Msg) -> Personality -> Cmd Msg
postPersonalityAfter toMsg personality =
    builder
        { method = HttpBuilder.post
        , path = "/phase/questionnaire"
        , expect = expectJson toMsg (D.field "questionnaires" Decode.qAfterExperiment) []
        }
        |> HttpBuilder.withJsonBody (Encode.personalityAfter personality)
        |> HttpBuilder.request


postExperience : (Result Http.Error (ApiResponse QAfterTrial) -> Msg) -> ValidExperience -> Cmd Msg
postExperience toMsg experience =
    builder
        { method = HttpBuilder.post
        , path = "/phase/questionnaire"
        , expect = expectJson toMsg (D.field "questionnaires" Decode.qAfterTrial) []
        }
        |> HttpBuilder.withJsonBody (Encode.experience experience)
        |> HttpBuilder.request


postPartnerTraits : (Result Http.Error (ApiResponse QAfterExperiment) -> Msg) -> ValidTraits -> Cmd Msg
postPartnerTraits toMsg traits =
    builder
        { method = HttpBuilder.post
        , path = "/phase/questionnaire"
        , expect = expectJson toMsg (D.field "questionnaires" Decode.qAfterExperiment) []
        }
        |> HttpBuilder.withJsonBody (Encode.traits traits)
        |> HttpBuilder.request


postStrategy : (Result Http.Error (ApiResponse QAfterExperiment) -> Msg) -> Strategy -> Cmd Msg
postStrategy toMsg strategy =
    builder
        { method = HttpBuilder.post
        , path = "/phase/questionnaire"
        , expect = expectJson toMsg (D.field "questionnaires" Decode.qAfterExperiment) []
        }
        |> HttpBuilder.withJsonBody (Encode.strategy strategy)
        |> HttpBuilder.request



-- BUILDING CALLS


baseUrl =
    "/api"


builderRoot :
    { method : String -> HttpBuilder.RequestBuilder ()
    , path : String
    , expect : Http.Expect a
    }
    -> HttpBuilder.RequestBuilder a
builderRoot { method, path, expect } =
    method path
        |> HttpBuilder.withHeader "Accept" "application/json"
        |> HttpBuilder.withExpect expect


builder :
    { method : String -> HttpBuilder.RequestBuilder ()
    , path : String
    , expect : Http.Expect a
    }
    -> HttpBuilder.RequestBuilder a
builder { method, path, expect } =
    builderRoot
        { method = method
        , path = baseUrl ++ path
        , expect = expect
        }


expectJson : (Result Http.Error (ApiResponse a) -> msg) -> D.Decoder a -> Feedback.Fields -> Http.Expect msg
expectJson toMsg decoder fields =
    Http.expectStringResponse toMsg <|
        \response ->
            case response of
                Http.BadUrl_ url ->
                    Err (Http.BadUrl url)

                Http.Timeout_ ->
                    Err Http.Timeout

                Http.NetworkError_ ->
                    Err Http.NetworkError

                Http.BadStatus_ metadata body ->
                    case D.decodeString (D.field "error" (Decode.feedback fields)) body of
                        Ok feedback ->
                            Ok (BadStatus metadata.statusCode feedback)

                        Err _ ->
                            Err (Http.BadStatus metadata.statusCode)

                Http.GoodStatus_ metadata body ->
                    case D.decodeString decoder body of
                        Ok value ->
                            Ok (GoodStatus value)

                        Err err ->
                            Err (Http.BadBody <| D.errorToString err)
