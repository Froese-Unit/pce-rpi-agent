module Decode exposing
    ( feedback
    , meta
    , phase
    , pids
    , players
    , qAfterExperiment
    , qAfterTrial
    , qPreExperiment
    , slots
    , socketMsg
    )

import Dict
import Feedback
import Json.Decode as D
import Types exposing (..)
import Utils


socketMsg : D.Decoder SocketMsg
socketMsg =
    D.field "tipe" D.string
        |> D.andThen socketMsgHelp


socketMsgHelp : String -> D.Decoder SocketMsg
socketMsgHelp tipe =
    case tipe of
        "error" ->
            D.map SocketMsgError (D.field "data" D.string)

        "phase" ->
            D.map SocketMsgPhase (D.field "data" phase)

        "meta" ->
            D.map SocketMsgMeta (D.field "data" meta)

        "players" ->
            D.map SocketMsgPlayers (D.field "data" players)

        _ ->
            D.fail <|
                "Trying to decode socket message, but tipe "
                    ++ tipe
                    ++ " is not supported"


players : D.Decoder Players
players =
    pProps player


player : D.Decoder Player
player =
    D.map4 Player
        (D.field "x" D.float)
        (D.field "button" D.bool)
        (D.field "ready" D.bool)
        (D.field "clicked" D.bool)


nullableTraining : D.Decoder (Maybe Training)
nullableTraining =
    D.nullable training


training : D.Decoder Training
training =
    D.string
        |> D.andThen trainingHelp


trainingHelp : String -> D.Decoder Training
trainingHelp s =
    case s of
        "visible" ->
            D.succeed Visible

        "hidden" ->
            D.succeed Hidden

        _ ->
            D.fail <|
                "Trying to decode message, but training statet "
                    ++ s
                    ++ " is unsupported"


phase : D.Decoder Phase
phase =
    D.field "phase" D.string
        |> D.andThen phaseHelp


phaseHelp : String -> D.Decoder Phase
phaseHelp s =
    case s of
        "pre_experiment" ->
            D.map3 PreExperiment
                (D.field "questionnaires" qPreExperiment)
                (D.field "config" config)
                (D.field "personality_questions_limit" <| D.nullable D.int)

        "pre_first_resting" ->
            D.succeed PreFirstResting

        "resting" ->
            D.map Resting (D.field "duration" D.int)

        "pre_trials" ->
            D.succeed PreTrials

        "trial" ->
            D.map2 Trial
                (D.field "duration" D.int)
                (D.field "config" config)

        "after_resting" ->
            D.succeed AfterResting

        "after_trial" ->
            D.map4 AfterTrial
                (D.field "training" nullableTraining)
                (D.field "next_phase" nextPhase)
                (D.field "preceding_trial_clicks" trialClicks)
                (D.field "questionnaires" qAfterTrial)

        "after_experiment" ->
            D.map2 AfterExperiment
                (D.field "questionnaires" qAfterExperiment)
                (D.field "personality_questions_limit" <| D.nullable D.int)

        "end" ->
            D.succeed End

        _ ->
            D.fail <|
                "Trying to decode message, but state "
                    ++ s
                    ++ " is unsupported"


qPreExperiment : D.Decoder QPreExperiment
qPreExperiment =
    D.map2 QPreExperiment
        (D.field "person" <| pProps D.bool)
        (D.field "personality_pre" <| pProps D.bool)


qAfterTrial : D.Decoder QAfterTrial
qAfterTrial =
    D.map QAfterTrial
        (D.field "experience" <| pProps D.bool)


qAfterExperiment : D.Decoder QAfterExperiment
qAfterExperiment =
    D.map3 QAfterExperiment
        (D.field "partner_traits" <| pProps D.bool)
        (D.field "personality_after" <| pProps D.bool)
        (D.field "strategy" <| pProps D.bool)


config : D.Decoder SpaceConfig
config =
    D.map8 SpaceConfig
        (D.field "env_width" D.float)
        (D.field "avatar_width" D.float)
        (D.field "static_width" D.float)
        (D.field "static0" D.float)
        (D.field "static1" D.float)
        (D.field "shadow_delta0" D.float)
        (D.field "shadow_delta1" D.float)
        (D.field "training" nullableTraining)


pProps : D.Decoder a -> D.Decoder (PProps a)
pProps decode =
    D.map2 PProps
        (D.field "p0" decode)
        (D.field "p1" decode)


nextPhase : D.Decoder NextPhase
nextPhase =
    D.field "type" D.string
        |> D.andThen nextPhaseHelp


nextPhaseHelp : String -> D.Decoder NextPhase
nextPhaseHelp p =
    case p of
        "trial" ->
            D.map TrialPhase
                (D.field "training" nullableTraining)

        "resting" ->
            D.succeed RestingPhase

        _ ->
            D.fail <| "Trying to decode NextPhase, but value " ++ p ++ " is not supported"


trialClicks : D.Decoder TrialClicks
trialClicks =
    pProps D.bool


meta : D.Decoder Meta
meta =
    D.map5 Meta
        (D.field "slots" slots)
        (D.field "pids" pids)
        (D.field "uuid" D.string)
        (D.field "lang" D.string)
        (D.field "training_trial_has_questionnaires" D.bool)


slots : D.Decoder Slots
slots =
    D.map3 Slots
        (D.field "experimenter" <| D.nullable D.string)
        (D.field "p0" <| D.nullable D.string)
        (D.field "p1" <| D.nullable D.string)


pids : D.Decoder Pids
pids =
    pProps <| D.nullable D.string


feedback : Feedback.Fields -> D.Decoder Feedback.Feedback
feedback fields =
    let
        checkKnown feedback_ =
            if Feedback.noKnownErrors feedback_ then
                D.fail ("Unknown errors: " ++ Feedback.getUnknown feedback_)

            else
                D.succeed feedback_
    in
    D.oneOf [ D.string, D.index 0 D.string ]
        |> D.dict
        |> D.map (toFeedback <| Dict.fromList fields)
        |> D.andThen checkKnown


toFeedback : Dict.Dict String String -> Dict.Dict String String -> Feedback.Feedback
toFeedback fields feedbackItems =
    let
        ( known, unknown ) =
            Dict.partition (\k v -> Dict.member k fields) feedbackItems

        finishFeedback processed =
            Feedback.feedback processed (Utils.dictToString unknown)
    in
    Dict.toList known
        |> List.map (\( k, e ) -> ( Dict.get k fields |> Maybe.withDefault k, e ))
        |> Dict.fromList
        |> finishFeedback
