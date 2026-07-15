module Types exposing (..)

import Dict
import Dropdown
import Feedback exposing (Feedback)
import Form
import Http
import I18Next exposing (Translations, initialTranslations, t)
import Json.Decode as D
import List



-- MESSAGES


type Msg
    = NoOp
    | Errored String
    | RecvMeta (Result Http.Error Meta)
    | RecvTranslations (Result Http.Error Translations)
    | SocketState (Result String Bool)
    | RecvSocketMsg (Result D.Error SocketMsg)
    | SelectSlot Slot
    | RecvSlots (Result Http.Error (ApiResponse Slots))
    | PidInput String
    | RecvPids (Result Http.Error (ApiResponse Pids))
    | SubmitPid
    | SubmitStartPhase
    | RecvPhase (Result Http.Error (ApiResponse Phase))
    | SubmitReady
    | RecvPlayers (Result Http.Error (ApiResponse Players))
    | PersonalityInput Int Int
    | PersonInputAge String
    | PersonSelectGender (Maybe String)
    | PersonGenderDropdownMsg (Dropdown.Msg String)
    | PersonSelectNationality (Maybe String)
    | PersonNationalityDropdownMsg (Dropdown.Msg String)
    | SubmitPerson
    | RecvPersons (Result Http.Error (ApiResponse QPreExperiment))
    | SubmitPersonalityPre
    | RecvPersonalitiesPre (Result Http.Error (ApiResponse QPreExperiment))
    | SubmitPersonalityAfter
    | RecvPersonalitiesAfter (Result Http.Error (ApiResponse QAfterExperiment))
    | ExperienceClickPresenceInput Int
    | ExperienceClickConfidenceInput Int
    | ExperienceAbsenceFrequencyInput Int
    | ExperienceAbsenceStrengthInput Int
    | SubmitExperience TrialClick
    | RecvExperiences (Result Http.Error (ApiResponse QAfterTrial))
    | PartnerTraitsInput Trait Float
    | SubmitPartnerTraits
    | RecvPartnerTraits (Result Http.Error (ApiResponse QAfterExperiment))
    | StrategySelfInput String
    | StrategyOtherInput String
    | StrategyCommentInput String
    | SubmitStrategy
    | RecvStrategies (Result Http.Error (ApiResponse QAfterExperiment))



-- API


type SocketMsg
    = SocketMsgError String
    | SocketMsgPhase Phase
    | SocketMsgMeta Meta
    | SocketMsgPlayers Players


type ApiResponse a
    = BadStatus Int Feedback
    | GoodStatus a



-- MODEL


type alias Model =
    { meta : Meta
    , langSet : Bool
    , translations : Translations
    , slotForm : Form.Model ()
    , pidForm : Form.Model String
    , startPhaseForm : Form.Model ()
    , personForm : Form.Model Person
    , personalityForm : Form.Model Personality
    , traitsForm : Form.Model Traits
    , experienceForm : Form.Model Experience
    , strategyForm : Form.Model Strategy
    , genderDropdown : Dropdown.State String
    , nationalityDropdown : Dropdown.State String
    , players : Players
    , exp : Exp
    }


type alias Meta =
    { slots : Slots
    , pids : Pids
    , uuid : Uuid
    , lang : String
    , trainingTrialHasQuestionnaires : Bool
    }


type alias Slots =
    { experimenter : Maybe Uuid
    , p0 : Maybe Uuid
    , p1 : Maybe Uuid
    }


type Exp
    = Connecting
    | Error String
    | Connected Phase


type alias PProps a =
    { p0 : a
    , p1 : a
    }


type alias Pids =
    PProps (Maybe String)


type alias Player =
    { x : Float, button : Bool, ready : Bool, clicked : Bool }


type alias Players =
    PProps Player


type alias QPreExperiment =
    { person : PProps Bool
    , personalityPre : PProps Bool
    }


type alias QAfterTrial =
    { experience : PProps Bool
    }


type alias QAfterExperiment =
    { partnerTraits : PProps Bool
    , personalityAfter : PProps Bool
    , strategy : PProps Bool
    }


type alias Uuid =
    String


type Slot
    = Experimenter
    | Participant P


type P
    = P0
    | P1


type NextPhase
    = TrialPhase (Maybe Training)
    | RestingPhase


type alias TrialClick =
    Bool


type alias TrialClicks =
    PProps TrialClick


type Phase
    = PreExperiment QPreExperiment SpaceConfig PersonalityConfig
      -- TODO: move form models to inside the phase models
    | PreFirstResting
    | Resting Duration
    | PreTrials
    | Trial Duration SpaceConfig
    | AfterResting
    | AfterTrial (Maybe Training) NextPhase TrialClicks QAfterTrial
    | AfterExperiment QAfterExperiment PersonalityConfig
    | End


type Training
    = Visible
    | Hidden


type alias Duration =
    Int


type alias PersonalityConfig =
    Maybe Int


type alias SpaceConfig =
    { envWidth : Float
    , avatarWidth : Float
    , staticWidth : Float
    , static0 : Float
    , static1 : Float
    , shadowDelta0 : Float
    , shadowDelta1 : Float
    , training : Maybe Training
    }



-- QUESTIONNAIRES


type alias Personality =
    Dict.Dict Int ( String, Int )


personalityQuestionsAll : Model -> Dict.Dict Int String
personalityQuestionsAll model =
    [ ( 1, "is-outgoing-sociable" )
    , ( 2, "is-compassionate-has-a-soft-heart" )
    , ( 3, "tends-to-be-disorganized" )
    , ( 4, "is-relaxed-handles-stress-well" )
    , ( 5, "has-few-artistic-interests" )
    , ( 6, "has-an-assertive-personality" )
    , ( 7, "is-respectful-treats-others-with-respect" )
    , ( 8, "tends-to-be-lazy" )
    , ( 9, "stays-optimistic-after-experiencing-a-setback" )
    , ( 10, "is-curious-about-many-different-things" )
    , ( 11, "rarely-feels-excited-or-eager" )
    , ( 12, "tends-to-find-fault-with-others" )
    , ( 13, "is-dependable-steady" )
    , ( 14, "is-moody-has-up-and-down-mood-swings" )
    , ( 15, "is-inventive-finds-clever-ways-to-do-things" )
    , ( 16, "tends-to-be-quiet" )
    , ( 17, "feels-little-sympathy-for-others" )
    , ( 18, "is-systematic-likes-to-keep-things-in-order" )
    , ( 19, "can-be-tense" )
    , ( 20, "is-fascinated-by-art-music-or-literature" )
    , ( 21, "is-dominant-acts-as-a-leader" )
    , ( 22, "starts-arguments-with-others" )
    , ( 23, "has-difficulty-getting-started-on-tasks" )
    , ( 24, "feels-secure-comfortable-with-self" )
    , ( 25, "avoids-intellectual-philosophical-discussions" )
    , ( 26, "is-less-active-than-other-people" )
    , ( 27, "has-a-forgiving-nature" )
    , ( 28, "can-be-somewhat-careless" )
    , ( 29, "is-emotionally-stable-not-easily-upset" )
    , ( 30, "has-little-creativity" )
    , ( 31, "is-sometimes-shy-introverted" )
    , ( 32, "is-helpful-and-unselfish-with-others" )
    , ( 33, "keeps-things-neat-and-tidy" )
    , ( 34, "worries-a-lot" )
    , ( 35, "values-art-and-beauty" )
    , ( 36, "finds-it-hard-to-influence-people" )
    , ( 37, "is-sometimes-rude-to-others" )
    , ( 38, "is-efficient-gets-things-done" )
    , ( 39, "often-feels-sad" )
    , ( 40, "is-complex-a-deep-thinker" )
    , ( 41, "is-full-of-energy" )
    , ( 42, "is-suspicious-of-others--intentions" )
    , ( 43, "is-reliable-can-always-be-counted-on" )
    , ( 44, "keeps-their-emotions-under-control" )
    , ( 45, "has-difficulty-imagining-things" )
    , ( 46, "is-talkative" )
    , ( 47, "can-be-cold-and-uncaring" )
    , ( 48, "leaves-a-mess-doesn-t-clean-up" )
    , ( 49, "rarely-feels-anxious-or-afraid" )
    , ( 50, "thinks-poetry-and-plays-are-boring" )
    , ( 51, "prefers-to-have-others-take-charge" )
    , ( 52, "is-polite-courteous-to-others" )
    , ( 53, "is-persistent-works-until-the-task-is-finished" )
    , ( 54, "tends-to-feel-depressed-blue" )
    , ( 55, "has-little-interest-in-abstract-ideas" )
    , ( 56, "shows-a-lot-of-enthusiasm" )
    , ( 57, "assumes-the-best-about-people" )
    , ( 58, "sometimes-behaves-irresponsibly" )
    , ( 59, "is-temperamental-gets-emotional-easily" )
    , ( 60, "is-original-comes-up-with-new-ideas" )
    ]
        |> List.map
            (\c ->
                ( Tuple.first c
                , t model.translations <| "connected.participant.person-questionnaire.personality.options." ++ Tuple.second c
                )
            )
        |> Dict.fromList


type Trait
    = Extraversion
    | Neuroticism
    | Openness
    | Agreeableness
    | Conscientiousness


type alias Traits =
    { extraversion : Maybe Float
    , neuroticism : Maybe Float
    , openness : Maybe Float
    , agreeableness : Maybe Float
    , conscientiousness : Maybe Float
    }


type alias ValidTraits =
    { extraversion : Float
    , neuroticism : Float
    , openness : Float
    , agreeableness : Float
    , conscientiousness : Float
    }


setTrait : Trait -> Maybe Float -> Traits -> Traits
setTrait trait value traits =
    case trait of
        Extraversion ->
            { traits | extraversion = value }

        Neuroticism ->
            { traits | neuroticism = value }

        Openness ->
            { traits | openness = value }

        Agreeableness ->
            { traits | agreeableness = value }

        Conscientiousness ->
            { traits | conscientiousness = value }


validTraits : Traits -> Maybe ValidTraits
validTraits t =
    Maybe.map5 ValidTraits
        t.extraversion
        t.neuroticism
        t.openness
        t.agreeableness
        t.conscientiousness


genderOptions : Model -> List String
genderOptions { translations } =
    [ "female", "male", "non-binary", "no-answer" ]
        |> List.map (\g -> t translations <| "connected.participant.person-questionnaire.gender." ++ g)


nationalityOptions : Model -> List String
nationalityOptions model =
    knownCountries model ++ [ t model.translations "connected.participant.person-questionnaire.nationality.other" ]


type alias Person =
    -- TODO: add a channel for comment, e.g. gender or nationality not in list, etc.
    { age : Maybe Int
    , gender : Maybe String
    , nationality : Maybe String
    }


type alias ValidPerson =
    { age : Int
    , gender : String
    , nationality : String
    }


validPerson : Person -> Maybe ValidPerson
validPerson p =
    Maybe.map3 ValidPerson
        p.age
        p.gender
        p.nationality


type alias Experience =
    { clickPresence : Maybe Int
    , clickConfidence : Maybe Int
    , absenceFrequency : Maybe Int
    , absenceStrength : Maybe Int
    }


type alias ValidExperience =
    { clickPresence : Int
    , clickConfidence : Int
    , absenceFrequency : Int
    , absenceStrength : Int
    }


absenceFrequencyNo : Int
absenceFrequencyNo =
    1


validExperience : Bool -> Experience -> Maybe ValidExperience
validExperience trialClick e =
    let
        ( clickPresence, clickConfidence ) =
            if trialClick then
                ( e.clickPresence, e.clickConfidence )

            else
                ( Just 0, Just 0 )

        absenceStrength =
            if e.absenceFrequency == Just absenceFrequencyNo then
                Just 0

            else
                e.absenceStrength
    in
    Maybe.map4 ValidExperience
        clickPresence
        clickConfidence
        e.absenceFrequency
        absenceStrength


type alias Strategy =
    { self : String
    , other : String
    , comment : String
    }



-- INIT


initModel : Bool -> Model
initModel langSet =
    { meta = initMeta
    , langSet = langSet
    , translations = initialTranslations
    , slotForm = Form.empty ()
    , pidForm = Form.empty ""
    , startPhaseForm = Form.empty ()
    , personForm = Form.empty initPerson
    , personalityForm = Form.empty initPersonality
    , traitsForm = Form.empty initTraits
    , experienceForm = Form.empty initExperience
    , strategyForm = Form.empty initStrategy
    , genderDropdown = Dropdown.init "gender-dropdown"
    , nationalityDropdown = Dropdown.init "nationality-dropdown"
    , players = initPlayers
    , exp = Connecting
    }


initMeta : Meta
initMeta =
    { slots = initSlots
    , pids = initPids
    , uuid = ""
    , lang = ""
    , trainingTrialHasQuestionnaires = True
    }


initSlots : Slots
initSlots =
    { experimenter = Nothing, p0 = Nothing, p1 = Nothing }


initPids : Pids
initPids =
    PProps Nothing Nothing


initPlayers : Players
initPlayers =
    { p0 = { x = 0, button = False, ready = False, clicked = False }
    , p1 = { x = 0, button = False, ready = False, clicked = False }
    }


initPerson : Person
initPerson =
    { age = Nothing
    , gender = Nothing
    , nationality = Nothing
    }


initPersonality : Personality
initPersonality =
    Dict.empty


initTraits : Traits
initTraits =
    { extraversion = Nothing
    , neuroticism = Nothing
    , openness = Nothing
    , agreeableness = Nothing
    , conscientiousness = Nothing
    }


initExperience : Experience
initExperience =
    { clickPresence = Nothing
    , clickConfidence = Nothing
    , absenceFrequency = Nothing
    , absenceStrength = Nothing
    }


initStrategy : Strategy
initStrategy =
    { self = ""
    , other = ""
    , comment = ""
    }



-- DATA


knownCountries : Model -> List String
knownCountries model =
    [ "abkhazia"
    , "afghanistan"
    , "albania"
    , "algeria"
    , "andorra"
    , "angola"
    , "antigua-and-barbuda"
    , "argentina"
    , "armenia"
    , "artsakh"
    , "australia"
    , "austria"
    , "azerbaijan"
    , "bahamas-the"
    , "bahrain"
    , "bangladesh"
    , "barbados"
    , "belarus"
    , "belgium"
    , "belize"
    , "benin"
    , "bhutan"
    , "bolivia"
    , "bosnia-and-herzegovina"
    , "botswana"
    , "brazil"
    , "brunei"
    , "bulgaria"
    , "burkina-faso"
    , "burundi"
    , "cambodia"
    , "cameroon"
    , "canada"
    , "cape-verde"
    , "central-african-republic"
    , "chad"
    , "chile"
    , "china"
    , "colombia"
    , "comoros"
    , "congo-democratic-republic-of-the"
    , "congo-republic-of-the"
    , "cook-islands"
    , "costa-rica"
    , "croatia"
    , "cuba"
    , "cyprus"
    , "czech-republic"
    , "denmark-kingdom-of"
    , "djibouti"
    , "dominica"
    , "dominican-republic"
    , "donetsk-people-s-republic"
    , "east-timor"
    , "ecuador"
    , "egypt"
    , "el-salvador"
    , "equatorial-guinea"
    , "eritrea"
    , "estonia"
    , "eswatini"
    , "ethiopia"
    , "fiji"
    , "finland"
    , "france"
    , "gabon"
    , "gambia-the"
    , "georgia"
    , "germany"
    , "ghana"
    , "greece"
    , "grenada"
    , "guatemala"
    , "guinea-bissau"
    , "guinea"
    , "guyana"
    , "haiti"
    , "honduras"
    , "hungary"
    , "iceland"
    , "india"
    , "indonesia"
    , "iran"
    , "iraq"
    , "ireland"
    , "israel"
    , "italy"
    , "ivory-coast"
    , "jamaica"
    , "japan"
    , "jordan"
    , "kazakhstan"
    , "kenya"
    , "kiribati"
    , "korea-north"
    , "korea-south"
    , "kosovo"
    , "kuwait"
    , "kyrgyzstan"
    , "laos"
    , "latvia"
    , "lebanon"
    , "lesotho"
    , "liberia"
    , "libya"
    , "liechtenstein"
    , "lithuania"
    , "luhansk-people-s-republic"
    , "luxembourg"
    , "madagascar"
    , "malawi"
    , "malaysia"
    , "maldives"
    , "mali"
    , "malta"
    , "marshall-islands"
    , "mauritania"
    , "mauritius"
    , "mexico"
    , "micronesia-federated-states-of"
    , "moldova"
    , "monaco"
    , "mongolia"
    , "montenegro"
    , "morocco"
    , "mozambique"
    , "myanmar"
    , "namibia"
    , "nauru"
    , "nepal"
    , "netherlands-kingdom-of-the"
    , "new-zealand"
    , "nicaragua"
    , "nigeria"
    , "niger"
    , "niue"
    , "northern-cyprus"
    , "north-macedonia"
    , "norway"
    , "oman"
    , "pakistan"
    , "palau"
    , "palestine"
    , "panama"
    , "papua-new-guinea"
    , "paraguay"
    , "peru"
    , "philippines"
    , "poland"
    , "portugal"
    , "qatar"
    , "romania"
    , "russia"
    , "rwanda"
    , "sahrawi-arab-democratic-republic"
    , "saint-kitts-and-nevis"
    , "saint-lucia"
    , "saint-vincent-and-the-grenadines"
    , "samoa"
    , "san-marino"
    , "são-tomé-and-príncipe"
    , "saudi-arabia"
    , "senegal"
    , "serbia"
    , "seychelles"
    , "sierra-leone"
    , "singapore"
    , "slovakia"
    , "slovenia"
    , "solomon-islands"
    , "somalia"
    , "somaliland"
    , "south-africa"
    , "south-ossetia"
    , "south-sudan"
    , "spain"
    , "sri-lanka"
    , "sudan"
    , "suriname"
    , "sweden"
    , "switzerland"
    , "syria"
    , "taiwan"
    , "tajikistan"
    , "tanzania"
    , "thailand"
    , "togo"
    , "tonga"
    , "transnistria"
    , "trinidad-and-tobago"
    , "tunisia"
    , "turkey"
    , "turkmenistan"
    , "tuvalu"
    , "uganda"
    , "ukraine"
    , "united-arab-emirates"
    , "united-kingdom"
    , "united-states"
    , "uruguay"
    , "uzbekistan"
    , "vanuatu"
    , "vatican-city"
    , "venezuela"
    , "vietnam"
    , "yemen"
    , "zambia"
    , "zimbabwe"
    ]
        |> List.map (\c -> t model.translations <| "connected.participant.person-questionnaire.nationality.countries." ++ c)
