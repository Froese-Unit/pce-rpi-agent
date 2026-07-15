module Utils exposing (..)

import Dict
import Http
import I18Next exposing (Delims(..), t, tr)
import List
import Types exposing (..)


getPProp : P -> PProps a -> a
getPProp p { p0, p1 } =
    case p of
        P0 ->
            p0

        P1 ->
            p1


mapPProps : (a -> b) -> PProps a -> PProps b
mapPProps f props =
    { p0 = f props.p0
    , p1 = f props.p1
    }


dictToString : Dict.Dict String String -> String
dictToString dict =
    Dict.toList dict
        |> List.map (\( k, v ) -> "\"" ++ k ++ "\": \"" ++ v ++ "\"")
        |> String.join ", "


ownSlot : Meta -> Maybe Slot
ownSlot meta =
    if Just meta.uuid == meta.slots.experimenter then
        Just Experimenter

    else if Just meta.uuid == meta.slots.p0 then
        Just <| Participant P0

    else if Just meta.uuid == meta.slots.p1 then
        Just <| Participant P1

    else
        Nothing


httpErrorToString : Http.Error -> String
httpErrorToString error =
    case error of
        Http.BadUrl msg ->
            "BadUrl: " ++ msg

        Http.Timeout ->
            "Timeout"

        Http.NetworkError ->
            "NetworkError"

        Http.BadStatus code ->
            "BadStatus: " ++ String.fromInt code

        Http.BadBody msg ->
            "BadBody: " ++ msg


slotToString : Slot -> String
slotToString slot =
    case slot of
        Experimenter ->
            "experimenter"

        Participant P0 ->
            "p0"

        Participant P1 ->
            "p1"


pToN : P -> String
pToN p =
    case p of
        P0 ->
            "0"

        P1 ->
            "1"


pToString : Model -> P -> String
pToString { translations } p =
    tr translations Curly "connected.participant-n" [ ( "id", pToN p ) ]


nextPhaseToString : Model -> NextPhase -> String
nextPhaseToString model nextPhase =
    case nextPhase of
        TrialPhase (Just Visible) ->
            t model.translations "connected.experimenter.after-trial.next-phase-trial-visible"

        TrialPhase (Just Hidden) ->
            t model.translations "connected.experimenter.after-trial.next-phase-trial-hidden"

        TrialPhase Nothing ->
            t model.translations "connected.experimenter.after-trial.next-phase-trial"

        RestingPhase ->
            t model.translations "connected.experimenter.after-trial.next-phase-resting"
