module Encode exposing
    ( experience
    , person
    , personalityAfter
    , personalityPre
    , pid
    , slot
    , strategy
    , traits
    , uuidSocketMsg
    )

import Dict
import Json.Encode as E
import Types exposing (..)
import Utils


uuidSocketMsg : String -> String
uuidSocketMsg uuid =
    E.object
        [ ( "tipe", E.string "uuid" )
        , ( "data", E.string uuid )
        ]
        |> E.encode 0


slot : Slot -> E.Value
slot slot_ =
    E.object [ ( "slot", E.string <| Utils.slotToString slot_ ) ]


pid : String -> E.Value
pid pid_ =
    E.object [ ( "pid", E.string pid_ ) ]


person : ValidPerson -> E.Value
person p =
    -- TODO: add question_text
    questionnaireHelp "person"
        [ { id = "age", text = "", answer = E.int p.age }
        , { id = "gender", text = "", answer = E.string p.gender }
        , { id = "nationality", text = "", answer = E.string p.nationality }
        ]


personalityPre : Personality -> E.Value
personalityPre p =
    questionnaireHelp "personality_pre" (personalityAnswers p)


personalityAfter : Personality -> E.Value
personalityAfter p =
    questionnaireHelp "personality_after" (personalityAnswers p)


personalityAnswers : Personality -> List Answer
personalityAnswers p =
    p
        |> Dict.toList
        |> List.map (\( id, ( text, answer ) ) -> { id = String.fromInt id, text = text, answer = E.int answer })


traits : ValidTraits -> E.Value
traits t =
    questionnaireHelp "partner_traits"
        [ { id = "extraversion", text = "", answer = E.float t.extraversion }
        , { id = "neuroticism", text = "", answer = E.float t.neuroticism }
        , { id = "openness", text = "", answer = E.float t.openness }
        , { id = "agreeableness", text = "", answer = E.float t.agreeableness }
        , { id = "conscientiousness", text = "", answer = E.float t.conscientiousness }
        ]


experience : ValidExperience -> E.Value
experience a =
    -- TODO: add question_text
    questionnaireHelp "experience"
        [ { id = "click_presence", text = "", answer = E.int a.clickPresence }
        , { id = "click_confidence", text = "", answer = E.int a.clickConfidence }
        , { id = "absence_frequency", text = "", answer = E.int a.absenceFrequency }
        , { id = "absence_strength", text = "", answer = E.int a.absenceStrength }
        ]


strategy : Strategy -> E.Value
strategy s =
    -- TODO: add question_text
    questionnaireHelp "strategy"
        [ { id = "self", text = "", answer = E.string s.self }
        , { id = "other", text = "", answer = E.string s.other }
        , { id = "comment", text = "", answer = E.string s.comment }
        ]



-- UTILS FOR QUESTIONNAIRES


questionnaireHelp : String -> List Answer -> E.Value
questionnaireHelp name answers =
    E.object
        [ ( name
          , E.list answerValue answers
          )
        ]


answerValue : Answer -> E.Value
answerValue a =
    E.object
        [ ( "question_id", E.string <| a.id )
        , ( "question_text", E.string <| a.text )
        , ( "answer", a.answer )
        ]


type alias Answer =
    { id : String
    , text : String
    , answer : E.Value
    }
