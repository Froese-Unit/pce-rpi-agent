module Form exposing
    ( Model
    , Status(..)
    , confirm
    , empty
    , fail
    , form
    , input
    , send
    , succeed
    )

import Feedback


type Status
    = Entering
    | Confirming
    | Sending


type alias Model a =
    { input : a, feedback : Feedback.Feedback, status : Status }


empty : a -> Model a
empty input_ =
    { input = input_, feedback = Feedback.empty, status = Entering }


form : a -> Feedback.Feedback -> Status -> Model a
form input_ feedback status =
    { input = input_, feedback = feedback, status = status }



-- HELPERS


input : Model a -> a -> Model a
input form_ input_ =
    form_
        |> setInput input_
        |> setFeedback Feedback.empty
        |> setStatus Entering


send : Model a -> Model a
send form_ =
    form_
        |> setFeedback Feedback.empty
        |> setStatus Sending


confirm : Model a -> Model a
confirm form_ =
    form_
        |> setFeedback Feedback.empty
        |> setStatus Confirming


fail : Model a -> Feedback.Feedback -> Model a
fail form_ feedback_ =
    form_
        |> setFeedback feedback_
        |> setStatus Entering


succeed : Model a -> a -> Model a
succeed form_ input_ =
    form_
        |> setInput input_
        |> setFeedback Feedback.empty
        |> setStatus Entering


setInput : a -> Model a -> Model a
setInput input_ { feedback, status } =
    form input_ feedback status


setFeedback : Feedback.Feedback -> Model a -> Model a
setFeedback feedback model =
    form model.input feedback model.status


setStatus : Status -> Model a -> Model a
setStatus status model =
    form model.input model.feedback status
