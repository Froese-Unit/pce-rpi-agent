module View exposing (genderDropdownConfig, nationalityDropdownConfig, view)

import Dict
import Dropdown
import Element as El
import Element.Background as Background
import Element.Border as Border
import Element.Font as Font
import Element.Input as Input
import Feedback
import Form
import Html exposing (Html)
import Html.Attributes as HA
import I18Next exposing (Delims(..), Translations, t, tr)
import Svg as S
import Svg.Attributes as SA
import Types exposing (..)
import Utils exposing (ownSlot, pToString)


view : Model -> Html Msg
view model =
    let
        ( header, ( recordingRunning, content ) ) =
            case model.exp of
                Connecting ->
                    ( El.none
                    , ( False, [ title (t model.translations "root.connecting") ] )
                    )

                Error msg ->
                    ( El.none
                    , ( False
                      , [ title (t model.translations "root.error")
                        , El.text msg
                        ]
                      )
                    )

                Connected phase ->
                    connectedView model phase

        recordingAttrs =
            if recordingRunning then
                [ Background.color black
                , Font.color white
                ]

            else
                []
    in
    El.layout ([ Font.family [ Font.typeface "Nimbus Sans", Font.sansSerif ] ] ++ recordingAttrs) <|
        El.column
            [ El.width <| El.px 900
            , El.centerX
            , El.height El.fill
            , El.padding 40
            , El.spacing 80
            ]
            [ El.el [ El.centerX ] header
            , El.column [ El.width El.fill, El.spacing 50 ] content
            ]


roundedGrayBoxAttrs : El.Color -> List (El.Attribute msg)
roundedGrayBoxAttrs fontColor =
    [ Font.color fontColor
    , Border.width 1
    , Border.color lightGray
    , Border.rounded 5
    , El.spacing 20
    , El.padding 10
    ]


connectedView : Model -> Phase -> ( El.Element Msg, ( Bool, List (El.Element Msg) ) )
connectedView model phase =
    case ( ownSlot model.meta, model.meta.pids.p0, model.meta.pids.p1 ) of
        ( Nothing, _, _ ) ->
            ( El.none
            , ( False, slotSelectionView model phase )
            )

        ( Just Experimenter, Just pid0, Just pid1 ) ->
            ( El.column (roundedGrayBoxAttrs darkGray)
                [ El.el [ El.centerX, Font.size 20 ] <| El.text (t model.translations "connected.experimenter.view")
                , El.row [ El.spacing 40 ]
                    [ El.column [ Font.size 16 ] [ El.text (pToString model P0), El.el [ Font.family [ Font.monospace ] ] (El.text pid0) ]
                    , El.column [ Font.size 16 ] [ El.text (pToString model P1), El.el [ Font.family [ Font.monospace ] ] (El.text pid1) ]
                    ]
                ]
            , ( False
              , connectedExperimenterView model phase
              )
            )

        ( Just Experimenter, _, _ ) ->
            ( El.text (t model.translations "connected.experimenter.view")
            , ( False
              , connectedExperimenterPidsView model
              )
            )

        ( Just (Participant P0), Just pid0, _ ) ->
            ( El.none, connectedParticipantView P0 model phase )

        ( Just (Participant P0), Nothing, _ ) ->
            ( El.none
            , ( False
              , connectedParticipantPidView model
              )
            )

        ( Just (Participant P1), _, Just pid1 ) ->
            ( El.none, connectedParticipantView P1 model phase )

        ( Just (Participant P1), _, Nothing ) ->
            ( El.none
            , ( False
              , connectedParticipantPidView model
              )
            )



-- SLOT SELECTION


slotSelectionView : Model -> Phase -> List (El.Element Msg)
slotSelectionView model phase =
    let
        disabled =
            model.slotForm.status /= Form.Entering

        slots =
            model.meta.slots

        { p0, p1 } =
            model.players
    in
    [ titleStyled [ ( [ El.centerX ], t model.translations "connected.select-slot" ) ]
    , El.row [ El.spacing 50, El.centerX ]
        [ selectableSlotView model phase Experimenter Nothing (slots.experimenter /= Nothing || disabled)
        , selectableSlotView model phase (Participant P0) (Just p0) (slots.p0 /= Nothing || disabled)
        , selectableSlotView model phase (Participant P1) (Just p1) (slots.p1 /= Nothing || disabled)
        ]
    ]


selectableSlotView : Model -> Phase -> Slot -> Maybe Player -> Bool -> El.Element Msg
selectableSlotView model phase slot maybePlayer disabled =
    let
        playerView_ =
            case maybePlayer of
                Nothing ->
                    El.none

                Just player ->
                    case phase of
                        PreExperiment _ config _ ->
                            El.html <| playerView config player 5

                        _ ->
                            El.none

        inner =
            case slot of
                Experimenter ->
                    El.el [ El.centerX ] <| El.text (t model.translations "connected.experimenter.root")

                Participant p ->
                    El.column [ El.spacing 20 ]
                        [ El.el [ El.centerX ] <| El.text (pToString model p)
                        , El.el [ El.centerX ] <| playerView_
                        ]

        attrs =
            if disabled then
                roundedGrayBoxAttrs lightGray

            else
                roundedGrayBoxAttrs darkGray
                    ++ [ El.mouseOver [ Background.color (El.rgb255 237 240 243) ]
                       , El.mouseDown [ Background.color lightGray ]
                       ]
    in
    Input.button
        attrs
        { onPress =
            if disabled then
                Nothing

            else
                Just <| SelectSlot slot
        , label = inner
        }



-- PID DEFINITION


connectedExperimenterPidsView : Model -> List (El.Element Msg)
connectedExperimenterPidsView model =
    [ title (t model.translations "connected.experimenter.pids-waiting")
    , connectedExperimenterPidView model P0 model.meta.pids.p0
    , connectedExperimenterPidView model P1 model.meta.pids.p1
    ]


connectedExperimenterPidView : Model -> P -> Maybe String -> El.Element msg
connectedExperimenterPidView model p maybePid =
    El.paragraph []
        [ El.text <| pToString model p ++ ": "
        , El.el [ Font.family [ Font.monospace ] ] <|
            El.text (Maybe.withDefault (t model.translations "connected.experimenter.pid-not-set") maybePid)
        ]


connectedParticipantPidView : Model -> List (El.Element Msg)
connectedParticipantPidView model =
    let
        { input, feedback, status } =
            model.pidForm
    in
    [ El.row [ El.spacing 20 ]
        -- TODO: use inputStyled everywhere
        [ inputStyled (status /= Form.Entering)
            [ Font.family [ Font.monospace ], El.spacing 20 ]
            PidInput
            input
            (Input.labelLeft [] <| El.text (t model.translations "connected.participant-id"))
        , button
            (status /= Form.Entering)
            SubmitPid
            (El.text (t model.translations "connected.send"))
        ]
    , El.paragraph [] [ El.text <| Feedback.getError "pid" feedback ]
    ]



-- EXPERIMENTER PHASE VIEWS


connectedExperimenterView : Model -> Phase -> List (El.Element Msg)
connectedExperimenterView model phase =
    case phase of
        PreExperiment qPreExperiment _ _ ->
            experimenterReadinessView model
                { currentPhase = t model.translations "connected.experimenter.pre-experiment.title"
                , explanation =
                    [ El.text (t model.translations "connected.experimenter.pre-experiment.instructions")
                    ]
                , startPhaseForm = model.startPhaseForm
                , required =
                    [ ( t model.translations "connected.experimenter.pre-experiment.person-questionnaire-done", qPreExperiment.person )
                    , ( t model.translations "connected.experimenter.pre-experiment.personality-questionnaire-done", qPreExperiment.personalityPre )
                    ]
                }

        PreFirstResting ->
            experimenterReadinessView model
                { currentPhase = t model.translations "connected.experimenter.pre-first-resting.title"
                , explanation = [ El.text (t model.translations "connected.experimenter.pre-first-resting.instructions") ]
                , startPhaseForm = model.startPhaseForm
                , required =
                    [ ( t model.translations "connected.ready-start", Utils.mapPProps .ready model.players )
                    ]
                }

        Resting duration ->
            [ subTitle (t model.translations "connected.experimenter.current-phase")
            , title (t model.translations "connected.experimenter.resting.title")
            , El.text (tr model.translations Curly "connected.experimenter.duration" [ ( "duration", String.fromInt duration ) ])
            ]

        PreTrials ->
            experimenterReadinessView model
                { currentPhase = t model.translations "connected.experimenter.pre-trials.title"
                , explanation = [ El.text (t model.translations "connected.experimenter.pre-trials.instructions") ]
                , startPhaseForm = model.startPhaseForm
                , required =
                    [ ( t model.translations "connected.ready-start", Utils.mapPProps .ready model.players )
                    ]
                }

        Trial duration config ->
            let
                titleText =
                    case config.training of
                        Nothing ->
                            t model.translations "connected.experimenter.trial.title"

                        Just Visible ->
                            t model.translations "connected.experimenter.trial.title-visible-training"

                        Just Hidden ->
                            t model.translations "connected.experimenter.trial.title-hidden-training"
            in
            [ El.row [ El.spacing 50, El.width El.fill, El.moveLeft 150 ]
                [ El.column [ El.width <| El.px 500, El.spacing 50, El.alignTop ]
                    [ subTitle (t model.translations "connected.experimenter.current-phase")
                    , titleStyled [ ( [ El.centerX ], titleText ) ]
                    , El.text (tr model.translations Curly "connected.experimenter.duration" [ ( "duration", String.fromInt duration ) ])
                    , experimenterLegendView model
                    ]
                , El.el [ El.width <| El.px 600 ] <| El.html <| spaceView config model.players Experimenter 1
                ]
            ]

        AfterResting ->
            experimenterReadinessView model
                { currentPhase = t model.translations "connected.experimenter.after-resting.title"
                , explanation =
                    [ El.text (t model.translations "connected.experimenter.after-resting.instructions")
                    , El.text " "
                    , El.text (t model.translations "connected.experimenter.after-resting.next-phase")
                    ]
                , startPhaseForm = model.startPhaseForm
                , required =
                    [ ( t model.translations "connected.ready-start", Utils.mapPProps .ready model.players )
                    ]
                }

        AfterTrial training nextPhase _ qAfterTrial ->
            let
                maybeParticipantExperience =
                    case ( model.meta.trainingTrialHasQuestionnaires, training ) of
                        ( False, Just _ ) ->
                            -- Training trial questionnaires are deactivated, and we're in training mode
                            []

                        _ ->
                            [ ( t model.translations "connected.experimenter.after-trial.questionnaire-completed"
                              , qAfterTrial.experience
                              )
                            ]
            in
            experimenterReadinessView model
                { currentPhase = t model.translations "connected.experimenter.after-trial.title"
                , explanation =
                    [ El.text (t model.translations "connected.experimenter.after-trial.instructions")
                    , El.text " "
                    , El.text (tr model.translations Curly "connected.experimenter.after-trial.next-phase" [ ( "next-phase", Utils.nextPhaseToString model nextPhase ) ])
                    ]
                , startPhaseForm = model.startPhaseForm
                , required =
                    maybeParticipantExperience
                        ++ [ ( t model.translations "connected.ready-start", Utils.mapPProps .ready model.players )
                           ]
                }

        AfterExperiment qAfterExperiment _ ->
            experimenterReadinessView model
                { currentPhase = t model.translations "connected.experimenter.after-experiment.title"
                , explanation =
                    [ El.text (t model.translations "connected.experimenter.after-experiment.instructions")
                    ]
                , startPhaseForm = model.startPhaseForm
                , required =
                    [ ( t model.translations "connected.experimenter.after-experiment.partner-traits-done", qAfterExperiment.partnerTraits )
                    , ( t model.translations "connected.experimenter.after-experiment.personality-questionnaire-done", qAfterExperiment.personalityAfter )
                    , ( t model.translations "connected.experimenter.after-experiment.stategy-questionnaire-done", qAfterExperiment.strategy )
                    ]
                }

        End ->
            [ subTitle (t model.translations "connected.experimenter.current-phase")
            , title (t model.translations "connected.experimenter.end.title")
            , El.text (t model.translations "connected.experimenter.end.content")
            ]


type alias ExperimenterReadinessConfig =
    { currentPhase : String
    , explanation : List (El.Element Msg)
    , startPhaseForm : Form.Model ()
    , required : List ( String, PProps Bool )
    }


experimenterReadinessView : Model -> ExperimenterReadinessConfig -> List (El.Element Msg)
experimenterReadinessView model { currentPhase, explanation, startPhaseForm, required } =
    let
        getPReqs p =
            required
                |> List.map (\( text, props ) -> ( text, p props ))

        allReady =
            List.foldr (\( _, { p0, p1 } ) prev -> prev && (p0 && p1))
                True
                required

        startPhaseButton =
            if allReady then
                button (startPhaseForm.status /= Form.Entering)
                    SubmitStartPhase
                    (El.text (t model.translations "connected.experimenter.start-next-phase"))

            else
                El.none
    in
    [ subTitle (t model.translations "connected.experimenter.current-phase")
    , title currentPhase
    , El.paragraph [] explanation
    , El.row [ El.spacing 40, El.centerX ]
        [ playerReadinessView model P0 (getPReqs .p0)
        , playerReadinessView model P1 (getPReqs .p1)
        ]
    , El.el [ El.centerX ] startPhaseButton
    ]


playerReadinessViewHelp : Model -> ( String, Bool ) -> El.Element Msg
playerReadinessViewHelp model ( text, ready ) =
    El.row [ Font.size 16 ]
        [ El.text <| text ++ ": "
        , El.el
            [ Font.color <|
                if ready then
                    darkGreen

                else
                    darkGray
            ]
            (El.text <|
                if ready then
                    t model.translations "connected.yes"

                else
                    t model.translations "connected.not-yet"
            )
        ]


playerReadinessView : Model -> P -> List ( String, Bool ) -> El.Element Msg
playerReadinessView model p readies =
    El.column
        [ El.spacing 20
        , El.padding 10
        , Border.color lightGray
        , Border.width 1
        , Border.rounded 5
        ]
        ([ El.el [ Font.size 24, El.centerX ] <| El.text <| Utils.pToString model p ]
            ++ List.map (playerReadinessViewHelp model) readies
        )



-- PARTICIPANT PHASE VIEWS


connectedParticipantView : P -> Model -> Phase -> ( Bool, List (El.Element Msg) )
connectedParticipantView p model phase =
    case phase of
        PreExperiment qPreExperiment _ pConfig ->
            ( False
            , participantQuestionnaireView
                [ ( Utils.getPProp p qPreExperiment.person, participantPersonView model )
                , ( Utils.getPProp p qPreExperiment.personalityPre
                  , participantPersonalityView
                        model
                        (t model.translations "connected.participant.person-questionnaire.personality.title")
                        SubmitPersonalityPre
                        pConfig
                        model.personalityForm
                  )
                ]
                [ subTitle (t model.translations "connected.participant.questionnaire.thank-you")
                , subTitle (t model.translations "connected.participant.questionnaire.next-do")
                , list
                    [ El.paddingEach { top = 0, right = 0, bottom = 0, left = 30 }
                    , El.spacing 20
                    ]
                    [ subTitleStyled
                        [ ( [], t model.translations "connected.participant.questionnaire.read-instructions-1" )
                        , ( [ Font.italic ], t model.translations "connected.perceptual-crossing-experiment" )
                        , ( [], t model.translations "connected.participant.questionnaire.read-instructions-2" )
                        ]
                    , subTitle (t model.translations "connected.participant.questionnaire.ask-your-questions")
                    ]
                ]
            )

        PreFirstResting ->
            ( False
            , participantQuestionnaireView
                [ ( .ready (Utils.getPProp p model.players)
                  , participantStartPhaseView model
                        True
                        [ subTitle (t model.translations "connected.participant.pre-first-resting.next-do")
                        , subTitle (t model.translations "connected.please")
                        , list
                            [ El.paddingEach { top = 0, right = 0, bottom = 0, left = 30 }
                            , El.spacing 20
                            ]
                            [ subTitle (t model.translations "connected.participant.pre-first-resting.moments-relax")
                            , subTitle (t model.translations "connected.participant.pre-first-resting.comfortable-position")
                            , subTitle (t model.translations "connected.participant.pre-first-resting.click-button-close-eyes")
                            ]
                        , subTitle (t model.translations "connected.participant.pre-first-resting.signify-complete")
                        ]
                  )
                ]
                [ title (t model.translations "connected.participant.pre-first-resting.please-eyes-closed-hands-table")
                , subTitle (t model.translations "connected.participant.pre-first-resting.resting-will-start")
                ]
            )

        Resting duration ->
            ( True
            , [ title (t model.translations "connected.participant.resting.title")
              , subTitle (t model.translations "connected.participant.resting.instructions")
              ]
            )

        PreTrials ->
            ( False
            , participantQuestionnaireView
                [ ( .ready (Utils.getPProp p model.players)
                  , participantStartPhaseView model
                        False
                        [ subTitleStyled
                            [ ( [], t model.translations "connected.participant.pre-trials.next-do-1" )
                            , ( [ Font.bold ], t model.translations "connected.participant.pre-trials.training" )
                            , ( [], t model.translations "connected.participant.pre-trials.next-do-2" )
                            ]
                        , subTitle (t model.translations "connected.participant.pre-trials.instructions")
                        ]
                  )
                ]
                (waitTrainingTrialText model)
            )

        Trial duration config ->
            case config.training of
                Just Visible ->
                    ( False
                    , [ El.row [ El.spacing 50, El.width El.fill, El.moveLeft 150 ]
                            [ El.column [ El.width <| El.px 500, El.spacing 50, El.alignTop ]
                                [ title (t model.translations "connected.participant.trial.training-title")
                                , subTitle (t model.translations "connected.participant.trial.sub-title")
                                , participantLegendView model p
                                , participantClickView model p
                                ]
                            , El.el [ El.width <| El.px 600 ] <| El.html <| spaceView config model.players (Participant p) 1
                            ]
                      ]
                    )

                Just Hidden ->
                    ( True
                    , ongoingTrainingHiddenText model
                    )

                Nothing ->
                    ( True
                    , ongoingTrialText model
                    )

        AfterResting ->
            ( False
            , participantQuestionnaireView
                [ ( .ready (Utils.getPProp p model.players)
                  , participantStartPhaseView model False (readinessAfterRestingText model)
                  )
                ]
                (waitTrialText model)
            )

        AfterTrial training nextPhase trialClicks qAfterTrial ->
            -- TODO: change the "training nextPhase" pair to a single trialTransition with only allowed values
            -- this will let us remove all the error states in the case blocks below
            let
                ( readiness, readyText ) =
                    case training of
                        Just Visible ->
                            case nextPhase of
                                TrialPhase (Just Visible) ->
                                    ( if model.meta.trainingTrialHasQuestionnaires then
                                        -- The questionnaire offers a step where
                                        -- the player has click "Next", so no
                                        -- need to add a a "next step"
                                        -- participant action
                                        []

                                      else
                                        -- This replaces the "next step" action
                                        -- to make sure each participant is
                                        -- ready
                                        [ ( .ready (Utils.getPProp p model.players)
                                          , participantStartPhaseView model False (startNextTrainingVisibleTrialsText model)
                                          )
                                        ]
                                    , waitTrainingTrialText model
                                    )

                                TrialPhase (Just Hidden) ->
                                    ( [ ( .ready (Utils.getPProp p model.players)
                                        , participantStartPhaseView model False (startTrainingHiddenTrialsText model)
                                        )
                                      ]
                                    , waitTrainingTrialText model
                                    )

                                TrialPhase Nothing ->
                                    ( [ ( False, errorPhaseTransitionText ) ], [] )

                                RestingPhase ->
                                    ( [ ( False, errorPhaseTransitionText ) ], [] )

                        Just Hidden ->
                            case nextPhase of
                                TrialPhase (Just Visible) ->
                                    ( [ ( False, errorPhaseTransitionText ) ], [] )

                                TrialPhase (Just Hidden) ->
                                    ( if model.meta.trainingTrialHasQuestionnaires then
                                        -- The questionnaire offers a step where
                                        -- the player has click "Next", so no
                                        -- need to add a a "next step"
                                        -- participant action
                                        []

                                      else
                                        -- This replaces the "next step" action
                                        -- to make sure each participant is
                                        -- ready
                                        [ ( .ready (Utils.getPProp p model.players)
                                          , participantStartPhaseView model False (startNextTrainingHiddenTrialsText model)
                                          )
                                        ]
                                    , waitTrainingTrialText model
                                    )

                                TrialPhase Nothing ->
                                    ( [ ( .ready (Utils.getPProp p model.players)
                                        , participantStartPhaseView model False (startRealTrialsText model)
                                        )
                                      ]
                                    , waitTrialText model
                                    )

                                RestingPhase ->
                                    ( [ ( False, errorPhaseTransitionText ) ], [] )

                        Nothing ->
                            case nextPhase of
                                TrialPhase (Just _) ->
                                    ( [ ( False, errorPhaseTransitionText ) ], [] )

                                TrialPhase Nothing ->
                                    ( []
                                    , waitTrialText model
                                    )

                                RestingPhase ->
                                    ( [ ( .ready (Utils.getPProp p model.players)
                                        , participantStartPhaseView model False (startRestingText model)
                                        )
                                      ]
                                    , waitRestingText model
                                    )

                maybeParticipantExperience =
                    case ( model.meta.trainingTrialHasQuestionnaires, training ) of
                        ( False, Just _ ) ->
                            -- Training trial questionnaires are deactivated, and we're in training mode
                            []

                        _ ->
                            [ ( Utils.getPProp p qAfterTrial.experience
                              , participantExperienceView model (Utils.getPProp p trialClicks)
                              )
                            ]
            in
            ( False
            , participantQuestionnaireView
                (maybeParticipantExperience ++ readiness)
                readyText
            )

        AfterExperiment qAfterExperiment pConfig ->
            ( False
            , participantQuestionnaireView
                [ ( Utils.getPProp p qAfterExperiment.partnerTraits
                  , participantPartnerTraitsView model
                  )
                , ( Utils.getPProp p qAfterExperiment.personalityAfter
                  , participantPersonalityView
                        model
                        (t model.translations "connected.participant.person-questionnaire.personality-post.title")
                        SubmitPersonalityAfter
                        pConfig
                        model.personalityForm
                  )
                , ( Utils.getPProp p qAfterExperiment.strategy, participantStrategyView model )
                ]
                (endText model)
            )

        End ->
            ( False
            , endText model
            )


participantPersonView : Model -> List (El.Element Msg)
participantPersonView model =
    let
        input =
            model.personForm.input

        status =
            model.personForm.status

        complete =
            -- TODO: use Validate here too?
            input.age /= Nothing && input.gender /= Nothing && input.nationality /= Nothing
    in
    [ El.textColumn [ El.spacing 20 ] [ subTitle (t model.translations "connected.participant.person-questionnaire.title") ]
    , Input.text
        [ El.padding 10
        , El.spacing 20
        , El.width <| El.px 80
        ]
        { onChange = PersonInputAge
        , text =
            case input.age of
                Nothing ->
                    ""

                Just age ->
                    String.fromInt age
        , placeholder = Nothing
        , label = Input.labelLeft [] (El.text (t model.translations "connected.participant.person-questionnaire.age"))
        }
    , El.row [ El.spacing 20 ]
        [ El.el [] <| El.text (t model.translations "connected.participant.person-questionnaire.gender.question")
        , Dropdown.view (genderDropdownConfig model) model.personForm model.genderDropdown
        ]
    , El.row [ El.spacing 20, El.width El.fill ]
        [ El.el [] <| El.text (t model.translations "connected.participant.person-questionnaire.nationality.question")
        , Dropdown.view (nationalityDropdownConfig model) model.personForm model.nationalityDropdown
        ]
    , if complete then
        button (status /= Form.Entering)
            SubmitPerson
            (El.text (t model.translations "connected.submit"))

      else
        El.text (t model.translations "connected.participant.questionnaire.task")
    ]


participantPersonalityQuestionView : Model -> Int -> String -> Maybe Int -> El.Element Msg
participantPersonalityQuestionView model id questionText maybeAnswer =
    let
        optionEl text =
            El.el [ Font.size 16 ] (El.text text)
    in
    Input.radioRow
        [ El.padding 10
        , El.spacing 20
        ]
        { onChange = PersonalityInput id
        , selected = maybeAnswer
        , label = Input.labelAbove [] (El.text questionText)
        , options =
            [ Input.option 1 (optionEl (t model.translations "connected.participant.questionnaire.disagree-strongly"))
            , Input.option 2 (optionEl (t model.translations "connected.participant.questionnaire.disagree-little"))
            , Input.option 3 (optionEl (t model.translations "connected.participant.questionnaire.neutral"))
            , Input.option 4 (optionEl (t model.translations "connected.participant.questionnaire.agree-little"))
            , Input.option 5 (optionEl (t model.translations "connected.participant.questionnaire.agree-strongly"))
            ]
        }


participantPersonalityView : Model -> String -> Msg -> PersonalityConfig -> Form.Model Personality -> List (El.Element Msg)
participantPersonalityView model titleString msg pConfig { input, status } =
    let
        personalityQuestions =
            case pConfig of
                Nothing ->
                    personalityQuestionsAll model

                Just limit ->
                    personalityQuestionsAll model
                        |> Dict.filter (\i q -> i <= limit)

        complete =
            personalityQuestions
                |> Dict.map (\id _ -> Dict.member id input)
                |> Dict.foldl (\_ answered sofar -> answered && sofar) True

        questionViews =
            personalityQuestions
                |> Dict.map
                    (\i q ->
                        participantPersonalityQuestionView
                            model
                            i
                            q
                            (Dict.get i input |> Maybe.map Tuple.second)
                    )
                |> Dict.foldr (\_ qView sofar -> qView :: sofar) []
    in
    [ El.textColumn [ El.spacing 20 ]
        [ subTitle titleString
        , El.paragraph [] [ El.text (t model.translations "connected.participant.person-questionnaire.personality.characteristics") ]
        ]
    , subTitle (t model.translations "connected.participant.person-questionnaire.personality.sub-title")
    , El.column [ El.spacing 30 ] questionViews
    , if complete then
        button (status /= Form.Entering) msg (El.text (t model.translations "connected.submit"))

      else
        El.text (t model.translations "connected.participant.questionnaire.task")
    ]


participantPartnerTraitsView : Model -> List (El.Element Msg)
participantPartnerTraitsView model =
    let
        input =
            model.traitsForm.input

        status =
            model.traitsForm.status

        complete =
            case validTraits input of
                Just _ ->
                    True

                Nothing ->
                    False

        completeButton =
            case complete of
                True ->
                    button (status /= Form.Entering)
                        SubmitPartnerTraits
                        (El.text (t model.translations "connected.submit"))

                False ->
                    El.text (t model.translations "connected.participant.after-experiment.partner-traits-instructions")

        slider trait label getValue =
            continuousSlider model
                { onChange = PartnerTraitsInput trait
                , labelText = label
                , value = getValue input
                , labels =
                    ( t model.translations "connected.very-little"
                    , t model.translations "connected.very-strong"
                    )
                }
    in
    [ partnerTraitsTitleText model
    , El.column [ El.spacing 20 ]
        [ slider Extraversion (t model.translations "connected.participant.after-experiment.partner-traits-extraversion") .extraversion
        , slider Neuroticism (t model.translations "connected.participant.after-experiment.partner-traits-neuroticism") .neuroticism
        , slider Openness (t model.translations "connected.participant.after-experiment.partner-traits-openness") .openness
        , slider Agreeableness (t model.translations "connected.participant.after-experiment.partner-traits-agreeableness") .agreeableness
        , slider Conscientiousness (t model.translations "connected.participant.after-experiment.partner-traits-conscientiousness") .conscientiousness
        ]
    ]
        ++ [ completeButton ]


participantExperienceView : Model -> Bool -> List (El.Element Msg)
participantExperienceView model trialClick =
    let
        input =
            model.experienceForm.input

        status =
            model.experienceForm.status

        completeAbsence =
            case input.absenceFrequency of
                Nothing ->
                    False

                Just absenceFrequency ->
                    if absenceFrequency == absenceFrequencyNo then
                        True

                    else
                        input.absenceStrength /= Nothing

        completeClick =
            case trialClick of
                False ->
                    True

                True ->
                    (input.clickPresence /= Nothing) && (input.clickConfidence /= Nothing)

        complete =
            completeAbsence && completeClick

        completeButton =
            case complete of
                True ->
                    button (status /= Form.Entering)
                        (SubmitExperience trialClick)
                        (El.text <| t model.translations "connected.submit")

                False ->
                    El.text <| t model.translations "connected.participant.questionnaire.please-answer"

        experienceClick =
            case trialClick of
                True ->
                    [ subTitle <| t model.translations "connected.participant.after-trial.title-button-pressed"
                    , El.column [ El.spacing 20 ]
                        [ participantExperienceClickPresenceView model input
                        , participantExperienceClickConfidenceView model input
                        ]
                    ]

                False ->
                    []
    in
    [ subTitle (t model.translations "connected.participant.after-trial.title")
    , El.column [ El.spacing 20 ]
        [ participantExperienceAbsenceFrequencyView model input
        , participantExperienceAbsenceStrengthView model input
        ]
    ]
        ++ experienceClick
        ++ [ completeButton ]


participantExperienceAbsenceFrequencyView : Model -> Experience -> El.Element Msg
participantExperienceAbsenceFrequencyView model input =
    Input.radioRow
        [ El.padding 10
        , El.spacing 20
        ]
        { onChange = ExperienceAbsenceFrequencyInput
        , selected = input.absenceFrequency
        , label =
            Input.labelAbove [] <|
                El.paragraph [] [ El.text (t model.translations "connected.participant.after-trial.absence-frequency") ]
        , options =
            [ Input.option absenceFrequencyNo <| El.text <| t model.translations "connected.No"
            , Input.option (absenceFrequencyNo + 1) <| El.text <| t model.translations "connected.participant.after-trial.once"
            , Input.option (absenceFrequencyNo + 2) <| El.text <| t model.translations "connected.participant.after-trial.a-few-times"
            , Input.option (absenceFrequencyNo + 3) <| El.text <| t model.translations "connected.participant.after-trial.many-times"
            , Input.option (absenceFrequencyNo + 4) <| El.text <| t model.translations "connected.participant.after-trial.all-the-time"
            ]
        }


participantExperienceAbsenceStrengthView : Model -> Experience -> El.Element Msg
participantExperienceAbsenceStrengthView model input =
    case input.absenceFrequency of
        Nothing ->
            El.none

        Just absenceFrequency ->
            if absenceFrequency == absenceFrequencyNo then
                El.none

            else
                El.el
                    [ El.paddingEach { top = 0, right = 0, bottom = 0, left = 30 }
                    , Border.widthEach { top = 0, right = 0, bottom = 0, left = 2 }
                    , Border.color lightGray
                    ]
                <|
                    Input.radio
                        [ El.padding 10
                        , El.spacing 20
                        ]
                        { onChange = ExperienceAbsenceStrengthInput
                        , selected = input.absenceStrength
                        , label =
                            Input.labelAbove [ El.padding 10 ] <|
                                El.text (t model.translations "connected.participant.after-trial.absence-strength")
                        , options =
                            [ Input.option 1 <| El.text <| t model.translations "connected.participant.after-trial.no-experience"
                            , Input.option 2 <| El.text <| t model.translations "connected.participant.after-trial.vague-impression"
                            , Input.option 3 <| El.text <| t model.translations "connected.participant.after-trial.almost-clear-experience"
                            , Input.option 4 <| El.text <| t model.translations "connected.participant.after-trial.clear-experience"
                            ]
                        }


participantExperienceClickPresenceView : Model -> Experience -> El.Element Msg
participantExperienceClickPresenceView model input =
    Input.radio
        [ El.padding 10
        , El.spacing 20
        ]
        { onChange = ExperienceClickPresenceInput
        , selected = input.clickPresence
        , label =
            Input.labelAbove [ El.padding 10 ] <|
                El.column [ El.spacing 10 ]
                    [ El.paragraph [] [ El.text <| t model.translations "connected.participant.after-trial.click-presence-1" ]
                    , El.paragraph [] [ El.text <| t model.translations "connected.participant.after-trial.click-presence-2" ]
                    ]
        , options =
            [ Input.option 1 <| El.text <| t model.translations "connected.participant.after-trial.no-experience"
            , Input.option 2 <| El.text <| t model.translations "connected.participant.after-trial.vague-impression"
            , Input.option 3 <| El.text <| t model.translations "connected.participant.after-trial.almost-clear-experience"
            , Input.option 4 <| El.text <| t model.translations "connected.participant.after-trial.clear-experience"
            ]
        }


participantExperienceClickConfidenceView : Model -> Experience -> El.Element Msg
participantExperienceClickConfidenceView model input =
    Input.radio
        [ El.padding 10
        , El.spacing 20
        ]
        { onChange = ExperienceClickConfidenceInput
        , selected = input.clickConfidence
        , label =
            Input.labelAbove [ El.padding 10 ] <|
                El.column [ El.spacing 10 ]
                    [ El.paragraph [] [ El.text <| t model.translations "connected.participant.after-trial.click-confidence-1" ]
                    , El.paragraph [] [ El.text <| t model.translations "connected.participant.after-trial.click-confidence-2" ]
                    ]
        , options =
            [ Input.option 1 <| El.text <| t model.translations "connected.participant.after-trial.no-confidence"
            , Input.option 2 <| El.text <| t model.translations "connected.participant.after-trial.low-confidence"
            , Input.option 3 <| El.text <| t model.translations "connected.participant.after-trial.medium-confidence"
            , Input.option 4 <| El.text <| t model.translations "connected.participant.after-trial.high-confidence"
            ]
        }


participantStrategyView : Model -> List (El.Element Msg)
participantStrategyView model =
    let
        input =
            model.strategyForm.input

        status =
            model.strategyForm.status
    in
    [ strategyCommentIntroText model
    , Input.multiline
        [ El.height (El.minimum (3 * 44) El.shrink) ]
        { onChange = StrategySelfInput
        , text = input.self
        , placeholder = Nothing
        , label =
            Input.labelAbove []
                (El.textColumn [ El.paddingXY 0 10, El.spacing 20 ]
                    (strategySelfText model)
                )
        , spellcheck = False
        }
    , Input.multiline
        [ El.height (El.minimum (3 * 44) El.shrink) ]
        { onChange = StrategyOtherInput
        , text = input.other
        , placeholder = Nothing
        , label =
            Input.labelAbove []
                (El.textColumn [ El.paddingXY 0 10, El.spacing 20 ]
                    (strategyOtherText model)
                )
        , spellcheck = False
        }
    , Input.multiline
        []
        { onChange = StrategyCommentInput
        , text = input.comment
        , placeholder = Nothing
        , label =
            Input.labelAbove []
                (El.textColumn [ El.paddingXY 0 10, El.spacing 20 ]
                    (commentText model)
                )
        , spellcheck = False
        }
    , button (status /= Form.Entering)
        SubmitStrategy
        (El.text (t model.translations "connected.submit"))
    ]


participantQuestionnaireView : List ( Bool, List (El.Element Msg) ) -> List (El.Element Msg) -> List (El.Element Msg)
participantQuestionnaireView steps finalText =
    let
        remainingSteps =
            List.filterMap
                (\( done, v ) ->
                    if done then
                        Nothing

                    else
                        Just v
                )
                steps
    in
    case remainingSteps of
        stepView :: _ ->
            stepView

        [] ->
            finalText


participantStartPhaseView : Model -> Bool -> List (El.Element Msg) -> List (El.Element Msg)
participantStartPhaseView model webButton text =
    let
        submit =
            if webButton then
                button (model.startPhaseForm.status /= Form.Entering)
                    SubmitReady
                    (El.text (t model.translations "connected.i-am-ready"))

            else
                subTitle (t model.translations "connected.long-press-move-on")
    in
    [ El.textColumn [ El.spacing 40 ] text
    , submit
    ]



-- QUESTIONNAIRE HELPERS


genderDropdownConfig : Model -> Dropdown.Config String Msg (Form.Model Person)
genderDropdownConfig model =
    let
        containerAttrs =
            [ El.width El.shrink, El.pointer ]

        selectAttrs =
            [ Border.width 1
            , Border.rounded 5
            , El.paddingXY 16 8
            , El.spacing 10
            , El.width El.fill
            ]

        listAttrs =
            [ Border.width 1
            , Border.rounded 5
            , El.width El.shrink
            , El.paddingXY 0 5
            , Background.color white
            ]

        itemToPrompt item =
            El.text item

        itemToElement selected highlighted item =
            El.el
                [ Background.color <|
                    if highlighted then
                        lightBlue

                    else if selected then
                        lightGreen

                    else
                        white
                , El.width El.fill
                , El.paddingXY 16 8
                , El.mouseOver [ Background.color lightGray ]
                ]
                (El.text item)
    in
    Dropdown.basic
        { itemsFromModel = always <| genderOptions model
        , selectionFromModel = .input >> .gender
        , dropdownMsg = PersonGenderDropdownMsg
        , onSelectMsg = PersonSelectGender
        , itemToPrompt = itemToPrompt
        , itemToElement = itemToElement
        }
        |> Dropdown.withContainerAttributes containerAttrs
        |> Dropdown.withSelectAttributes selectAttrs
        |> Dropdown.withListAttributes listAttrs
        |> Dropdown.withPromptElement (El.el [] <| El.text <| "-- " ++ t model.translations "connected.select" ++ " --")


nationalityDropdownConfig : Model -> Dropdown.Config String Msg (Form.Model Person)
nationalityDropdownConfig model =
    let
        containerAttrs =
            -- TODO With is not enough when a long nationalaty value is chosen
            [ El.width (El.fill |> El.minimum 300), El.pointer ]

        selectAttrs =
            [ Border.width 1
            , Border.rounded 5
            , El.paddingXY 16 8
            , El.spacing 10
            , El.width El.fill
            ]

        searchAttrs =
            [ Border.width 0, El.padding 0 ]

        listAttrs =
            [ Border.width 1
            , Border.rounded 5
            , El.width El.shrink
            , El.paddingXY 0 5
            , Background.color white
            ]

        itemToPrompt item =
            El.text item

        itemToElement selected highlighted item =
            El.el
                [ Background.color <|
                    if highlighted then
                        lightBlue

                    else if selected then
                        lightGreen

                    else
                        white
                , El.width El.fill
                , El.paddingXY 16 8
                , El.mouseOver [ Background.color lightGray ]
                ]
                (El.text item)
    in
    Dropdown.filterable
        { itemsFromModel = always (nationalityOptions model)
        , selectionFromModel = .input >> .nationality
        , dropdownMsg = PersonNationalityDropdownMsg
        , onSelectMsg = PersonSelectNationality
        , itemToPrompt = itemToPrompt
        , itemToElement = itemToElement
        , itemToText = identity
        }
        |> Dropdown.withContainerAttributes containerAttrs
        |> Dropdown.withSelectAttributes selectAttrs
        |> Dropdown.withListAttributes listAttrs
        |> Dropdown.withSearchAttributes searchAttrs
        |> Dropdown.withPromptElement (El.el [] <| El.text <| "-- " ++ t model.translations "connected.select" ++ " --")



-- SLIDER HELPERS


likertSliderAttrs : List (El.Attribute msg)
likertSliderAttrs =
    [ El.height (El.px 70)
    , El.width (El.px 200)
    , El.moveUp 22

    -- Here is where we're creating/styling the "track"
    , El.behindContent
        (El.el
            [ El.width El.fill
            , El.height (El.px 2)
            , El.centerY
            , Background.color lightGray
            , Border.rounded 2
            ]
            El.none
        )
    ]


likertThumb : Maybe Int -> Input.Thumb
likertThumb inputValue =
    let
        visibilityAttrs =
            case inputValue of
                Nothing ->
                    [ El.padding 7 ]

                Just _ ->
                    [ El.width (El.px 16)
                    , El.height (El.px 16)
                    , Border.rounded 8
                    , Border.width 1
                    , Border.color (El.rgb 0.5 0.5 0.5)
                    , Background.color (El.rgb 1 1 1)
                    ]

        handle =
            El.column
                [ El.centerX, El.paddingXY 0 5 ]
                [ El.el
                    [ El.width <| El.px 8
                    , El.height <| El.px 8
                    , Background.color darkGray
                    , El.centerX
                    , El.rotate (degrees 45)
                    , El.moveDown 4
                    ]
                    El.none
                , El.el
                    [ El.padding 10
                    , Border.rounded 50
                    , Background.color darkGray
                    , Font.color white
                    , Font.size 15
                    ]
                    (El.text <| Maybe.withDefault "Drag here" <| Maybe.map String.fromInt inputValue)
                ]
    in
    Input.thumb <| visibilityAttrs ++ [ El.below handle ]


type alias LikertParams msg =
    { onChange : Int -> msg
    , labelText : String
    , value : Maybe Int
    , labels : ( String, String )
    }


sliderLabel : String -> El.Element msg
sliderLabel label =
    sliderLabelHelp label [ El.alignTop ]


sliderLabelBottom : String -> El.Element msg
sliderLabelBottom label =
    sliderLabelHelp label [ El.alignBottom ]


sliderLabelHelp : String -> List (El.Attribute msg) -> El.Element msg
sliderLabelHelp label attrs =
    El.el
        ([ El.paddingXY 0 4, Font.color mediumGray ] ++ attrs)
        (El.text label)


likertSlider : LikertParams msg -> El.Element msg
likertSlider { onChange, labelText, value, labels } =
    El.column
        []
        [ El.text labelText
        , El.row [ El.padding 10, El.spacing 15 ]
            [ sliderLabel (Tuple.first labels)
            , Input.slider likertSliderAttrs
                { onChange = round >> onChange
                , label = Input.labelHidden ""
                , min = 1
                , max = 7
                , step = Just 1
                , value = Maybe.map toFloat value |> Maybe.withDefault 4
                , thumb = likertThumb value
                }
            , sliderLabel (Tuple.second labels)
            ]
        ]


type alias ContinuousSliderParams msg =
    { onChange : Float -> msg
    , labelText : String
    , value : Maybe Float
    , labels : ( String, String )
    }


continuousSliderAttrs : List (El.Attribute msg)
continuousSliderAttrs =
    [ El.height (El.px 80)
    , El.width (El.px 400)
    , El.moveDown 27

    -- Here is where we're creating/styling the "track"
    , El.behindContent
        (El.el
            [ El.width El.fill
            , El.height (El.px 2)
            , El.centerY
            , Background.color lightGray
            , Border.rounded 2
            ]
            El.none
        )
    ]


continuousThumb : Model -> Maybe Float -> String -> Input.Thumb
continuousThumb model inputValue label =
    let
        ( visibilityAttrs, instructions ) =
            case inputValue of
                Nothing ->
                    ( [ El.padding 7 ]
                    , " " ++ t model.translations "connected.(drag-here)"
                    )

                Just _ ->
                    ( [ El.width (El.px 16)
                      , El.height (El.px 16)
                      , Border.rounded 8
                      , Border.width 1
                      , Border.color (El.rgb 0.5 0.5 0.5)
                      , Background.color (El.rgb 1 1 1)
                      ]
                    , ""
                    )

        handle =
            El.column
                [ El.centerX, El.paddingXY 0 5 ]
                [ El.el
                    [ El.padding 12
                    , Border.rounded 50
                    , Background.color darkGray
                    , Font.color white
                    ]
                    (El.text <| label ++ instructions)
                , El.el
                    [ El.width <| El.px 8
                    , El.height <| El.px 8
                    , Background.color darkGray
                    , El.centerX
                    , El.rotate (degrees 45)
                    , El.moveUp 4
                    ]
                    El.none
                ]
    in
    Input.thumb <| visibilityAttrs ++ [ El.above handle ]


continuousSlider : Model -> ContinuousSliderParams msg -> El.Element msg
continuousSlider model { onChange, labelText, value, labels } =
    El.column
        []
        [ El.row [ El.padding 10, El.spacing 15 ]
            [ sliderLabelBottom (Tuple.first labels)
            , Input.slider continuousSliderAttrs
                { onChange = onChange
                , label = Input.labelHidden ""
                , min = 0
                , max = 1
                , step = Just 0.01
                , value = value |> Maybe.withDefault 0.5
                , thumb = continuousThumb model value labelText
                }
            , sliderLabelBottom (Tuple.second labels)
            ]
        ]



-- VIRTUAL SPACE


playerView : SpaceConfig -> Player -> Float -> S.Svg msg
playerView config p zoom =
    S.svg
        [ SA.width "150px"
        , SA.height "auto"
        , SA.viewBox "0 0 300 300"
        ]
        [ S.circle
            [ SA.cx "150"
            , SA.cy "150"
            , SA.r "100"
            , SA.fill "transparent"
            , SA.stroke "#aaa"
            , SA.strokeWidth <| String.fromFloat (0.5 * zoom)
            ]
            []
        , spacePlayerView config p0Color p False zoom
        , spaceButtonView p0Color p zoom
        ]


p0Color : String
p0Color =
    "#ffac05ff"


p1Color : String
p1Color =
    "#b45160ff"


spaceView : SpaceConfig -> Players -> Slot -> Float -> S.Svg msg
spaceView config { p0, p1 } slot zoom =
    let
        ( p0ShowButton, p1ShowButton ) =
            case slot of
                Experimenter ->
                    ( True, True )

                Participant P0 ->
                    ( not p0.clicked, False )

                Participant P1 ->
                    ( False, not p1.clicked )
    in
    S.svg
        [ SA.width "100%"
        , SA.height "auto"
        , SA.viewBox "40 40 260 260"
        ]
        [ S.circle
            [ SA.cx "150"
            , SA.cy "150"
            , SA.r "100"
            , SA.fill "transparent"
            , SA.stroke "#aaa"
            , SA.strokeWidth <| String.fromFloat (0.5 * zoom)
            ]
            []
        , spacePlayerView config p0Color p0 p0ShowButton zoom
        , spaceShadowView config p0Color (p0.x + config.shadowDelta0) zoom
        , spaceStaticView config p1Color config.static0 zoom -- this static is touchable by player 0, so the same color as the other stuff player 0 touches
        , spacePlayerView config p1Color p1 p1ShowButton zoom
        , spaceShadowView config p1Color (p1.x + config.shadowDelta1) zoom
        , spaceStaticView config p0Color config.static1 zoom -- this static is touchable by player 1, so the same color as the other stuff player 1 touches
        ]


experimenterLegendView : Model -> El.Element msg
experimenterLegendView { translations, players, meta } =
    let
        p0 =
            players.p0

        p0id =
            case meta.pids.p0 of
                Nothing ->
                    t translations "connected.no-participant-id"

                Just id ->
                    id

        p1 =
            players.p1

        p1id =
            case meta.pids.p1 of
                Nothing ->
                    t translations "connected.no-participant-id"

                Just id ->
                    id

        clicked =
            t translations "connected.space.has-clicked"

        notClicked =
            t translations "connected.space.click-pending"

        items =
            [ ( spacePlayerViewAlone p0Color
              , "P0: "
                    ++ p0id
                    ++ ". "
                    ++ (if p0.clicked then
                            clicked

                        else
                            notClicked
                       )
              )
            , ( spacePlayerViewAlone p1Color
              , "P1: "
                    ++ p1id
                    ++ ". "
                    ++ (if p1.clicked then
                            clicked

                        else
                            notClicked
                       )
              )
            ]
    in
    El.column [ El.spacing 20 ] <|
        [ El.text (t translations "connected.space.legend") ]
            ++ List.map legendElementView items


participantLegendView : Model -> P -> El.Element msg
participantLegendView { translations } p =
    let
        ( pColor, otherColor ) =
            case p of
                P0 ->
                    ( p0Color, p1Color )

                P1 ->
                    ( p1Color, p0Color )

        items =
            [ ( spacePlayerViewAlone pColor, t translations "connected.space.your-avatar" )
            , ( spaceShadowViewAlone pColor, t translations "connected.space.your-shadow" )
            , ( spaceStaticViewAlone pColor, t translations "connected.space.your-static-object" )
            , ( spacePlayerViewAlone otherColor, t translations "connected.space.partners-avatar" )
            , ( spaceShadowViewAlone otherColor, t translations "connected.space.partners-shadow" )
            , ( spaceStaticViewAlone otherColor, t translations "connected.space.partners-static-object" )
            ]
    in
    El.column [ El.spacing 20 ] <|
        [ El.text (t translations "connected.space.legend-detail") ]
            ++ List.map legendElementView items


legendElementView : ( S.Svg msg, String ) -> El.Element msg
legendElementView ( svg, text ) =
    El.row [ El.spacing 10 ]
        [ El.el [ El.width <| El.px 20 ] <|
            El.html <|
                S.svg
                    [ SA.width "100%"
                    , SA.height "auto"
                    , SA.viewBox "-4 -4 8 8"
                    ]
                    [ svg ]
        , El.text text
        ]


participantClickView : Model -> P -> El.Element msg
participantClickView model p =
    participantClickViewHelp model (pX p model.players)


participantClickViewHelp : Model -> Player -> El.Element msg
participantClickViewHelp model p =
    case p.clicked of
        True ->
            El.paragraph [ El.spacing 10 ] <|
                [ El.text (t model.translations "connected.space.you-clicked") ]

        False ->
            El.text ""


pX : P -> { p0 : a, p1 : a } -> a
pX p { p0, p1 } =
    case p of
        P0 ->
            p0

        P1 ->
            p1


spaceButtonView : String -> Player -> Float -> S.Svg msg
spaceButtonView color player zoom =
    S.circle
        [ SA.cx "50"
        , SA.cy "50"
        , SA.r "15"
        , SA.fill <|
            if player.button then
                color

            else
                "transparent"
        , SA.stroke color
        , SA.strokeWidth <| String.fromFloat (0.5 * zoom)
        ]
        []


spacePlayerView : SpaceConfig -> String -> Player -> Bool -> Float -> S.Svg msg
spacePlayerView config color player showButton zoom =
    S.g []
        [ spaceObjectViewInSpace config
            { moving = True
            , stroke = color
            , fill = color
            , size = config.avatarWidth * zoom
            , x = player.x
            }
        , spaceObjectViewInSpace config
            { moving = True
            , stroke =
                if player.button && showButton then
                    color

                else
                    "transparent"
            , fill = "transparent"
            , size = config.avatarWidth * zoom * 4
            , x = player.x
            }
        ]


spacePlayerViewAlone : String -> S.Svg msg
spacePlayerViewAlone color =
    spaceObjectViewAlone
        { moving = True
        , stroke = color
        , fill = color
        , size = 4
        , x = 0
        }


spaceShadowView : SpaceConfig -> String -> Float -> Float -> S.Svg msg
spaceShadowView config color x zoom =
    spaceObjectViewInSpace config
        { moving = True
        , stroke = color
        , fill = "transparent"
        , size = config.avatarWidth * zoom
        , x = x
        }


spaceShadowViewAlone : String -> S.Svg msg
spaceShadowViewAlone color =
    spaceObjectViewAlone
        { moving = True
        , stroke = color
        , fill = "transparent"
        , size = 4
        , x = 0
        }


spaceStaticView : SpaceConfig -> String -> Float -> Float -> S.Svg msg
spaceStaticView config color x zoom =
    spaceObjectViewInSpace config
        { moving = False
        , stroke = color
        , fill = "transparent"
        , size = config.staticWidth * zoom
        , x = x
        }


spaceStaticViewAlone : String -> S.Svg msg
spaceStaticViewAlone color =
    spaceObjectViewAlone
        { moving = False
        , stroke = color
        , fill = "transparent"
        , size = 4
        , x = 0
        }


type alias ObjectViewConfig =
    { moving : Bool
    , stroke : String
    , fill : String
    , size : Float
    , x : Float
    }


spaceObjectViewInSpace : SpaceConfig -> ObjectViewConfig -> S.Svg msg
spaceObjectViewInSpace spaceConfig objectViewConfig =
    let
        angle =
            -360 * objectViewConfig.x / spaceConfig.envWidth
    in
    spaceObjectViewHelp
        objectViewConfig
        [ SA.transform <| "rotate(" ++ String.fromFloat angle ++ ", 150, 150) translate(150, 50)" ]


spaceObjectViewAlone : ObjectViewConfig -> S.Svg msg
spaceObjectViewAlone objectViewConfig =
    spaceObjectViewHelp objectViewConfig []


spaceObjectViewHelp : ObjectViewConfig -> List (S.Attribute msg) -> S.Svg msg
spaceObjectViewHelp { moving, stroke, fill, size, x } moreAttrs =
    let
        strokeWidth =
            size / 4

        ( base, attrs ) =
            case moving of
                False ->
                    ( S.rect
                    , [ SA.x <| String.fromFloat <| strokeWidth / 2 - size / 2
                      , SA.y <| String.fromFloat <| strokeWidth / 2 - size / 2
                      , SA.width <| String.fromFloat <| size - strokeWidth
                      , SA.height <| String.fromFloat <| size - strokeWidth
                      ]
                    )

                True ->
                    ( S.circle
                    , [ SA.cx <| String.fromFloat 0
                      , SA.cy <| String.fromFloat 0
                      , SA.r <| String.fromFloat (size / 2 - strokeWidth / 2)
                      ]
                    )
    in
    base
        (attrs
            ++ [ SA.fill fill
               , SA.stroke stroke
               , SA.strokeWidth <| String.fromFloat strokeWidth
               ]
            ++ moreAttrs
        )
        []



-- VIEW UTILS


titleSize : Int
titleSize =
    38


subTitleSize : Int
subTitleSize =
    28


white : El.Color
white =
    El.rgb 1 1 1


black : El.Color
black =
    El.rgb 0 0 0


lightGray : El.Color
lightGray =
    El.rgb255 204 204 204


mediumGray : El.Color
mediumGray =
    El.rgb255 110 110 110


darkGray : El.Color
darkGray =
    El.rgb255 60 60 60


darkGreen : El.Color
darkGreen =
    El.rgb255 71 121 80


lightGreen : El.Color
lightGreen =
    El.rgb255 205 255 198


lightBlue : El.Color
lightBlue =
    El.rgb255 168 196 213


button : Bool -> msg -> El.Element msg -> El.Element msg
button disabled onPress label =
    let
        attrs =
            if disabled then
                [ Font.color darkGray
                , Border.color (El.rgb255 214 217 221)
                , Background.color (El.rgb255 249 250 251)
                ]

            else
                [ Font.color (El.rgb255 38 92 131)
                , Border.color (El.rgb255 214 217 221)
                , Background.color (El.rgb255 249 250 251)
                , El.mouseOver [ Background.color (El.rgb255 237 240 243) ]
                , El.mouseDown [ Background.color lightGray, Border.color lightGray, Font.color darkGray ]
                ]
    in
    Input.button
        ([ Border.width 1
         , El.padding 8
         ]
            ++ attrs
        )
        { onPress =
            if disabled then
                Nothing

            else
                Just onPress
        , label = label
        }



{-
   input : Bool -> (String -> Msg) -> String -> Input.Label Msg -> El.Element Msg
   input disabled onChange text label =
       inputStyled disabled [] onChange text label
-}


inputStyled : Bool -> List (El.Attribute Msg) -> (String -> Msg) -> String -> Input.Label Msg -> El.Element Msg
inputStyled disabled styles onChange text label =
    let
        disabledStyle =
            if disabled then
                [ Background.color lightGray
                ]

            else
                []
    in
    Input.text (styles ++ disabledStyle)
        { onChange =
            if disabled then
                \_ -> NoOp

            else
                onChange
        , text = text
        , placeholder = Nothing
        , label = label
        }


title : String -> El.Element msg
title text =
    titleStyled [ ( [], text ) ]


titleStyled : List ( List (El.Attribute msg), String ) -> El.Element msg
titleStyled stylesText =
    El.el [ Font.size titleSize ] <|
        El.paragraph []
            (List.map (\st -> El.el (Tuple.first st) (El.text <| Tuple.second st)) stylesText)


subTitle : String -> El.Element msg
subTitle text =
    subTitleStyled [ ( [], text ) ]


subTitleStyled : List ( List (El.Attribute msg), String ) -> El.Element msg
subTitleStyled stylesText =
    El.el [ Font.size subTitleSize ] <|
        El.paragraph []
            (List.map (\st -> El.el (Tuple.first st) (El.text <| Tuple.second st)) stylesText)



{-
   onEnter : msg -> El.Attribute msg
   onEnter msg =
       El.htmlAttribute
           (Html.Events.on "keyup"
               (D.field "key" D.string
                   |> D.andThen
                       (\key ->
                           if key == "Enter" then
                               D.succeed msg

                           else
                               D.fail "Not the enter key"
                       )
               )
           )
-}
-- TEXT


list : List (El.Attribute msg) -> List (El.Element msg) -> El.Element msg
list attrs items =
    El.column attrs <|
        List.map
            (\item -> El.el [ El.htmlAttribute (HA.style "display" "list-item") ] item)
            items


waitTrainingTrialText model =
    [ title (t model.translations "connected.participant.pre-trials.training-title")
    , subTitle (t model.translations "connected.participant.pre-trials.training-wait")
    ]


waitTrialText model =
    [ title (t model.translations "connected.participant.pre-trials.real-title")
    , subTitle (t model.translations "connected.participant.pre-trials.real-wait")
    ]


waitRestingText model =
    [ title (t model.translations "connected.participant.after-trial.wait-resting-title")
    , subTitle (t model.translations "connected.participant.after-trial.wait-resting-sub-title")
    ]


errorPhaseTransitionText =
    [ title "An error occured"
    , subTitle "We reached an inconsistent phase transition. Please show this to the experimenter."
    ]


readinessAfterRestingText model =
    [ subTitle (t model.translations "connected.participant.after-resting.back-to-trials") ]


startNextTrainingVisibleTrialsText model =
    [ subTitle (t model.translations "connected.participant.pre-trials.training-trial-again") ]


startTrainingHiddenTrialsText model =
    [ subTitleStyled
        [ ( [], t model.translations "connected.participant.pre-trials.training-trial-hidden-1" )
        , ( [ Font.bold ], t model.translations "connected.participant.pre-trials.hide" )
        , ( [], t model.translations "connected.participant.pre-trials.training-trial-hidden-2" )
        ]
    ]


startNextTrainingHiddenTrialsText model =
    [ subTitle (t model.translations "connected.participant.pre-trials.training-trial-hidden-again") ]


startRealTrialsText model =
    [ subTitleStyled
        [ ( [], t model.translations "connected.participant.pre-trials.real-trial-1" )
        , ( [ Font.bold ], t model.translations "connected.participant.pre-trials.real" )
        , ( [], t model.translations "connected.participant.pre-trials.real-trial-2" )
        ]
    ]


ongoingTrainingHiddenText model =
    [ title (t model.translations "connected.participant.trial.training-title")
    , subTitle (t model.translations "connected.participant.trial.please-eyes-closed")
    , subTitle (t model.translations "connected.participant.trial.instructions")
    ]


ongoingTrialText model =
    [ title (t model.translations "connected.participant.trial.real-title")
    , subTitle (t model.translations "connected.participant.trial.please-eyes-closed")
    , subTitle (t model.translations "connected.participant.trial.instructions")
    ]


partnerTraitsTitleText model =
    subTitle (t model.translations "connected.participant.after-resting.partner-traits-instructions")


strategyCommentIntroText model =
    subTitle (t model.translations "connected.participant.after-experiment.strategy-questionnaire")


strategySelfText model =
    [ subTitleStyled
        [ ( [], t model.translations "connected.participant.after-experiment.strategy-self-1" )
        , ( [], t model.translations "connected.you" )
        , ( [], t model.translations "connected.participant.after-experiment.strategy-self-2" )
        ]
    ]


strategyOtherText model =
    [ subTitleStyled
        [ ( [], t model.translations "connected.participant.after-experiment.strategy-other-1" )
        , ( [ Font.bold ], t model.translations "connected.your-partner" )
        , ( [], t model.translations "connected.participant.after-experiment.strategy-other-2" )
        ]
    ]


commentText model =
    [ subTitle (t model.translations "connected.participant.after-experiment.comment") ]


endText model =
    [ title (t model.translations "connected.participant.after-experiment.end-title")
    , subTitle (t model.translations "connected.participant.after-experiment.end-content")
    ]


startRestingText model =
    [ subTitle (t model.translations "connected.participant.after-trial.resting-next")
    , subTitle (t model.translations "connected.please")
    , list
        [ El.paddingEach { top = 0, right = 0, bottom = 0, left = 30 }
        , El.spacing 20
        ]
        [ subTitle (t model.translations "connected.participant.after-trial.resting-relax")
        , subTitle (t model.translations "connected.participant.after-trial.resting-comfortable")
        ]
    ]
