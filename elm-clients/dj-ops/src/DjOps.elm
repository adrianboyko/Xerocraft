module DjOps exposing (..)

-- Standard
import Html exposing (Html, div, text, select, option, input, p, br, span, table, tr, td, i)
import Html as Html
import Html.Attributes exposing (style, href, attribute)
import Html.Events exposing (onInput, on, on)
import Http as Http
import Time exposing (Time, second)
import Date exposing (Date)
import Regex
import Char
import Keyboard
import Set exposing (Set)
import Task exposing (Task)
import Process
import Array exposing (Array)
import Maybe exposing (Maybe(..), withDefault)
import List exposing (head, tail)

-- Third Party
import Material
import Material.Button as Button
import Material.Textfield as Textfield
import Material.Table as Table
import Material.Options as Opts exposing (css)
import Material.Icon as Icon
import Material.Layout as Layout
import Material.Color as Color
import Material.Footer as Footer
import Material.Badge as Badge
import DatePicker
import List.Nonempty as NonEmpty exposing (Nonempty)
import List.Extra as ListX
import Hex as Hex
import Dialog as Dialog
import Maybe.Extra as MaybeX exposing (isJust, isNothing)
import Update.Extra as UpdateX exposing (updateModel)

-- Local
import ClockTime as CT
import Duration as Dur
import PointInTime as PiT exposing (PointInTime)
import CalendarDate as CD
import XisRestApi as XisApi
import DjangoRestFramework as DRF


-----------------------------------------------------------------------------
-- CONSTANTS
-----------------------------------------------------------------------------

startTabId = 0
tracksTabId = 1
underwritingTabId = 2
finishTabId = 3

-- For Start Tab
userIdFieldId = [startTabId, 1]
passwordFieldId = [startTabId, 2]

-- For Tracks Tab
numTrackRows = 60
artistColId = 0
titleColId = 1
durationColId = 2


-----------------------------------------------------------------------------
-- MAIN
-----------------------------------------------------------------------------

main =
  Html.programWithFlags
    { init = init
    , view = view
    , update = update
    , subscriptions = subscriptions
    }


-----------------------------------------------------------------------------
-- MODEL
-----------------------------------------------------------------------------

-- These are params from the server. Elm docs tend to call them "flags".

type alias Flags =
  { csrfToken : Maybe String
  , xisRestFlags : XisApi.XisRestFlags
  }

type RfidReaderState
  = Nominal
  | CheckingAnRfid Int  -- Int counts the number of seconds waited
  | HitAnHttpErr Http.Error
  | FoundRfidToBe Bool  -- Bool is True if Rfid was registered, else False.

type alias TracksTabEntry =
  { lastChanged : Maybe PointInTime
  , playListEntryId : Maybe Int
  , artist : String
  , title : String
  , duration : String
  , saving : Bool
  }

newTracksTabEntry : Maybe Int -> String -> String -> String -> Bool -> TracksTabEntry
newTracksTabEntry id artist title duration saving =
  TracksTabEntry Nothing id artist title duration saving

blankTracksTabEntry : TracksTabEntry
blankTracksTabEntry =
  newTracksTabEntry Nothing "" "" "" False

type alias Model =
  { errMsgs : List String
  , mdl : Material.Model
  , xis : XisApi.Session Msg
  , currTime : PointInTime
  , selectedTab : Int
  , shows : List XisApi.Show
  , selectedShow : Maybe XisApi.Show
  , selectedShowDate : Maybe Date
  , showInstance : Maybe XisApi.ShowInstance  -- This is derived from selectedShow + selectedShowDate.
  , datePicker : DatePicker.DatePicker
  , member : Maybe XisApi.Member
  , nowPlaying : Maybe XisApi.NowPlaying
  --- Tracks Tab model:
  , tracksTabEntries : Array TracksTabEntry
  --- RFID Reader state:
  , state : RfidReaderState
  , typed : String
  , rfidsToCheck : List Int
  , loggedAsPresent : Set Int
  --- Credentials:
  , userid : Maybe String
  , password : Maybe String
  }


init : Flags -> ( Model, Cmd Msg )
init flags =
  let
    auth = case flags.csrfToken of  -- TODO: REMOVE THIS
      Just csrf -> DRF.LoggedIn csrf
      Nothing -> DRF.NoAuthorization
    getShowsCmd = model.xis.listShows ShowList_Result
    nowPlayingCmd = model.xis.nowPlaying NowPlaying_Result
    (datePicker, datePickerCmd ) = DatePicker.init
    model =
      { errMsgs = []
      , mdl = Material.model
      , xis = XisApi.createSession flags.xisRestFlags auth
      , currTime = 0
      , selectedTab = 0
      , shows = []
      , selectedShow = Nothing
      , selectedShowDate = Nothing
      , showInstance = Nothing
      , datePicker = datePicker
      , member = Nothing
      , nowPlaying = Nothing
      --- Tracks Tab model:
      , tracksTabEntries = Array.repeat numTrackRows blankTracksTabEntry
      --- RFID Reader state:
      , state = Nominal
      , typed = ""
      , rfidsToCheck = []
      , loggedAsPresent = Set.empty
      --- Credentials:
      , userid = Nothing
      , password = Nothing
      }
  in
    ( model
    , Cmd.batch
      [ getShowsCmd
      , nowPlayingCmd
      , Cmd.map SetDatePicker datePickerCmd
      , Layout.sub0 Mdl
      ]
    )


-----------------------------------------------------------------------------
-- UPDATE
-----------------------------------------------------------------------------


type
  Msg
  = AcknowledgeDialog
  | Authenticate_Result (Result Http.Error XisApi.AuthenticationResult)
  | CheckNowPlaying
  | KeyDownRfid Keyboard.KeyCode
  | FetchTracksTabData
  | Login_Clicked
  | ManualPlayListEntryUpsert_Result (Result Http.Error XisApi.ManualPlayListEntry)
  | Mdl (Material.Msg Msg)
  | MemberListResult (Result Http.Error (DRF.PageOf XisApi.Member))
  | MemberPresentResult (Result Http.Error XisApi.VisitEvent)
  | NowPlaying_Result (Result Http.Error XisApi.NowPlaying)
  | NowPlaying_Tick -- see Tick Time
  | PasswordInput String
  | RfidTick  -- see Tick Time
  | SaveTracksTabEntry Int  -- Row to save
  | ShowInstanceList_Result (Result Http.Error (DRF.PageOf XisApi.ShowInstance))
  | ShowList_Result (Result Http.Error (DRF.PageOf XisApi.Show))
  | ShowWasChosen String  -- ID of chosen show, as a String.
  | SelectTab Int
  | SetDatePicker DatePicker.Msg
  | Tick Time
  | TrackFieldUpdate Int Int String  -- row, col, value
  | UseridInput String



update : Msg -> Model -> ( Model, Cmd Msg )
update action model =
  let xis = model.xis
  in case action of

    AcknowledgeDialog ->
      ( { model
        | errMsgs = []
        , state = Nominal
        , typed = ""
        , rfidsToCheck = []
        , loggedAsPresent = Set.empty
        }
      , Cmd.none
      )

    Authenticate_Result (Ok {isAuthentic, authenticatedMember}) ->
      let
        errMsgs = if isAuthentic then [] else ["Bad userid and/or password provided.", "Close this dialog and try again."]
      in
        ({model | member=authenticatedMember, errMsgs=errMsgs}, Cmd.none)
        |> UpdateX.andThen update FetchTracksTabData

    CheckNowPlaying ->
      ( model
      , model.xis.nowPlaying NowPlaying_Result
      )

    FetchTracksTabData ->
      fetchTracksTabData model

    KeyDownRfid code ->
      let
        typed = case code of
          16 -> model.typed  -- i.e. ignore this shift code.
          190 -> ">"  -- i.e. start char resets the typed buffer.
          c -> model.typed ++ (c |> Char.fromCode |> String.fromChar)
        finds = Regex.find Regex.All delimitedRfidNum typed
      in
        if List.isEmpty finds then
          -- There aren't any delimited rfids
          ({model | typed=typed}, Cmd.none)
        else
          -- There ARE delimited rfids, so pull them out, process them, and pass a modified s through.
          let
            delimitedMatches = List.map .match finds
            hexMatches = List.map (String.dropLeft 1) delimitedMatches
            hexToInt = String.toLower >> Hex.fromString
            resultIntMatches = List.map hexToInt hexMatches
            intMatches = List.filterMap Result.toMaybe resultIntMatches
            newRfidsToCheck = ListX.unique (model.rfidsToCheck++intMatches)
          in
            checkAnRfid {model | typed=typed, rfidsToCheck=newRfidsToCheck}

    Login_Clicked ->
      case (model.userid, model.password) of
        (Just id, Just pw) ->
          (model, model.xis.authenticate id pw Authenticate_Result)
        _ ->
          (model, Cmd.none)

    ManualPlayListEntryUpsert_Result (Ok mple) ->
      case Array.get mple.data.sequence model.tracksTabEntries of
        Just tte ->
          let
            newTte = {tte | lastChanged = Nothing, saving = False, playListEntryId = Just mple.id }
            newTtes = Array.set mple.data.sequence newTte model.tracksTabEntries
          in
            ( { model | tracksTabEntries = newTtes }
            , Cmd.none
            )
        Nothing ->
          -- TODO: Shouldn't ever get here. Log the fact that we did?
          (model, Cmd.none)

    Mdl msg_ ->
      Material.update Mdl msg_ model

    MemberListResult (Ok {results}) ->
      case results of

        member :: [] ->  -- Exactly ONE match. Good.
          let
            cmd2 =
              if Set.member member.id model.loggedAsPresent then
                Cmd.none
              else
                model.xis.createVisitEvent
                  { who = model.xis.memberUrl member.id
                  , when = model.currTime
                  , eventType = XisApi.VET_Present
                  , method = XisApi.VEM_FrontDesk
                  , reason = Nothing
                  }
                  MemberPresentResult
            newModel =
              { model
              | state = Nominal
              , rfidsToCheck = []
              , typed = ""
              , loggedAsPresent = Set.insert member.id model.loggedAsPresent
              }
          in
            (newModel, cmd2)

        [] ->  -- ZERO matches. Bad. Should not happen.
          -- TODO: Log something to indicate a program logic error.
          checkAnRfid {model | state=FoundRfidToBe False}

        member :: members ->  -- More than one match. Bad. Should not happen.
          -- TODO: Log something to indicate a program logic error.
          checkAnRfid {model | state=FoundRfidToBe False}

    MemberPresentResult (Ok _) ->
      -- Don't need to do anything when this succeeds.
      (model, Cmd.none)

    NowPlaying_Result (Ok np) ->
      let
        nowPlayingCmd = model.xis.nowPlaying NowPlaying_Result
        delaySeconds = case np.track of
          Just t ->
            let
              rs = t.remainingSeconds
            in
              if rs > 0 then rs * second
              else if rs < 1 && rs > -5 then 0.1 * second
              else 1 * second
          Nothing -> 1 * second
      in
        ( { model | nowPlaying = Just np }
        , delay delaySeconds CheckNowPlaying
        )

    NowPlaying_Tick ->
      case model.nowPlaying of
        Just np ->
          case np.track of
            Just t ->
              let
                updatedTrack = {t | remainingSeconds = t.remainingSeconds - 1}
                updatedNowPlaying = {np | track = Just updatedTrack}
                updatedModel = {model | nowPlaying = Just updatedNowPlaying}
              in
                (updatedModel, Cmd.none)
            Nothing ->
                (model, Cmd.none)
        Nothing ->
          (model, Cmd.none)

    PasswordInput s ->
      ({model | password = Just s}, Cmd.none)

    RfidTick ->
      case model.state of
        CheckingAnRfid wc ->
          ({model | state=CheckingAnRfid (wc+1)}, Cmd.none)
        _ ->
          (model, Cmd.none)

    SaveTracksTabEntry row ->
      case Array.get row model.tracksTabEntries of
        Just tte ->
          case tte.lastChanged of
            Just lastChanged ->
              if (model.currTime - lastChanged) > 3*second && (not tte.saving) then
                let
                  newTte = {tte | saving = True}
                  newTtes = Array.set row newTte model.tracksTabEntries
                in
                  ( { model | tracksTabEntries = newTtes }
                  , upsertManualPlayListEntry model row tte
                  )
              else
                (model, Cmd.none)
            Nothing ->
              -- This means that the row was already saved.
              (model, Cmd.none)
        Nothing ->
          -- TODO: Shouldn't get here. Log unexpected situation?
          (model, Cmd.none)

    SelectTab k ->
      ( { model | selectedTab = k }, Cmd.none )

    SetDatePicker msg ->
      let
        (newDatePicker, datePickerCmd, dateEvent) =
          DatePicker.update DatePicker.defaultSettings msg model.datePicker
      in
        case dateEvent of
          DatePicker.NoChange ->
            ( { model | datePicker = newDatePicker }
            , Cmd.map SetDatePicker datePickerCmd
            )
          DatePicker.Changed d ->
            ( { model | selectedShowDate = d, datePicker = newDatePicker }
            , Cmd.map SetDatePicker datePickerCmd
            )
            |> UpdateX.andThen update FetchTracksTabData

    ShowInstanceList_Result (Ok {count, results}) ->
      let
        showInstance = head results
        tracksForTab = showInstance |> Maybe.map (.data >> .manualPlayList) |> withDefault []
      in
        ({model | showInstance = showInstance }, Cmd.none)
          |> updateModel (populateTracksTabData tracksForTab)

    ShowList_Result (Ok {results}) ->
      ({model | shows=results}, Cmd.none)

    ShowList_Result (Err error) ->
      ({model | errMsgs=[toString error]}, Cmd.none)

    ShowWasChosen idStr ->
      case idStr |> String.toInt |> Result.toMaybe of
        Just id ->
          let
            show = ListX.find (\s->s.id==id) model.shows
          in
            ({ model | selectedShow = show}, Cmd.none)
              |> UpdateX.andThen update FetchTracksTabData
        Nothing ->
          let
            -- Should be impossible to get here since ids in question are integer PKs from database.
            dummy = Debug.log "Bad Show ID" idStr
          in
            (model, Cmd.none)

    Tick newTime ->
      let
        newModel = { model | currTime = newTime }
      in
        (newModel, Cmd.none)
          |> UpdateX.andThen update RfidTick
          |> UpdateX.andThen update NowPlaying_Tick

    TrackFieldUpdate row col val ->
      let
        tte1 = withDefault blankTracksTabEntry (Array.get row model.tracksTabEntries)
        tte2 = {tte1 | lastChanged = Just model.currTime, saving = False }
        tte3 =
          if col == artistColId then {tte2 | artist = val}
          else if col == titleColId then {tte2 | title = val}
          else if col == durationColId then {tte2 | duration = val}
          else tte2 -- TODO: Note unexpected situation.
        newModel = { model | tracksTabEntries = Array.set row tte3 model.tracksTabEntries}
      in
        (newModel, delay (5*second) (SaveTracksTabEntry row))

    UseridInput s ->
      ({model | userid = Just s}, Cmd.none)

    -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --

    Authenticate_Result (Err e) ->
      ({model | errMsgs=[toString e]}, Cmd.none)

    ManualPlayListEntryUpsert_Result (Err e) ->
      ({model | errMsgs=[toString e]}, Cmd.none)

    MemberListResult (Err e) ->
      ({model | state=HitAnHttpErr e}, Cmd.none)

    MemberPresentResult (Err e) ->
      ({model | state=HitAnHttpErr e}, Cmd.none)

    NowPlaying_Result (Err e) ->
      let
        dummy = toString e |> Debug.log "NowPlaying_Result"
      in
        ({model | nowPlaying = Nothing}, Cmd.none)

    ShowInstanceList_Result (Err e) ->
      let
        dummy = toString e |> Debug.log "ShowInstanceList_Result"
      in
        (model, Cmd.none)


fetchTracksTabData : Model -> (Model, Cmd Msg)
fetchTracksTabData model =
  case (model.member, model.selectedShow, model.selectedShowDate) of

    (Just member, Just show, Just selectedShowDate) ->
      let
        showFilter = XisApi.SI_ShowEquals show.id
        dateFilter = XisApi.SI_DateEquals <| CD.fromDate selectedShowDate
        fetchCmd = model.xis.listShowInstances [showFilter, dateFilter] ShowInstanceList_Result
      in
        (model, fetchCmd)
    _ ->
      -- TODO: Unload TracksTab data here?
      (model, Cmd.none)


populateTracksTabData : List XisApi.ManualPlayListEntry -> Model -> Model
populateTracksTabData ples model =
  let
    newModel = { model | tracksTabEntries = Array.repeat numTrackRows blankTracksTabEntry }
  in
    populateTracksTabData_Helper newModel ples


populateTracksTabData_Helper : Model -> List XisApi.ManualPlayListEntry -> Model
populateTracksTabData_Helper model plesRemaining =
  case plesRemaining of
    [] ->
      model
    ple::ples ->
      let
        seq = ple.data.sequence
        tte = newTracksTabEntry (Just ple.id) ple.data.artist ple.data.title ple.data.duration False
        newModel = { model | tracksTabEntries = Array.set seq tte model.tracksTabEntries }
      in
        populateTracksTabData_Helper newModel ples


upsertManualPlayListEntry : Model -> Int -> TracksTabEntry -> Cmd Msg
upsertManualPlayListEntry model row tte =
  case model.showInstance of
    Just showInstance ->
      let
        mpleData = XisApi.ManualPlayListEntryData
          (model.xis.showInstanceUrl showInstance.id) row tte.artist tte.title tte.duration
      in
        case tte.playListEntryId of
          Just idToUpdate ->
            model.xis.replaceManualPlayListEntry
              (DRF.Resource idToUpdate mpleData)
              ManualPlayListEntryUpsert_Result
          Nothing ->
            model.xis.createManualPlayListEntry
              mpleData
              ManualPlayListEntryUpsert_Result

    Nothing ->
      -- TODO: Log unexpected result? Show instance should have been created by now.
      Cmd.none


-----------------------------------------------------------------------------
-- VIEW
-----------------------------------------------------------------------------

tabs model =
  (
    [ text "start"
    , tracksTabTitle model
    , text "underwriting"
    , text "finish"
    ]
  , [ Color.background <| Color.color Color.DeepPurple Color.S400
    , Color.text <| Color.color Color.Green Color.S400
    ]
  )

tracksTabTitle : Model -> Html Msg
tracksTabTitle model =
  let
    filter = isJust << .playListEntryId
    trackCount = model.tracksTabEntries |> Array.filter filter |> Array.length
  in
    if trackCount > 0 then
      Opts.span [Badge.add (toString trackCount)] [text "tracks"]
    else
      -- Margin-right, here, takes up same space as missing badge so that tab title spacing remains the same.
      span [style ["margin-right"=>"24px"]] [text "tracks"]


view : Model -> Html Msg
view model =
  div []
  [ Layout.render Mdl model.mdl
    [ Layout.fixedHeader
    , Layout.fixedTabs
    , Layout.onSelectTab SelectTab
    , Layout.selectedTab model.selectedTab
    ]
    { header = layout_header model
    , drawer = []
    , tabs = tabs model
    , main = [layout_main model]
    }
  , Dialog.view <| rfid_dialog_config model
  , Dialog.view <| err_dialog_config model
  ]


err_dialog_config : Model -> Maybe (Dialog.Config Msg)
err_dialog_config model =

  if List.length model.errMsgs > 0 then
    Just
      { closeMessage = Just AcknowledgeDialog
      , containerClass = Nothing
      , containerId = Nothing
      , header = Just (text "😱 Error")
      , body = Just <| div [] <| List.map ((p [])<<List.singleton<<text) model.errMsgs
      , footer = Nothing
      }
  else
    Nothing

tagattr x = attribute x x


showSelector : Model -> Html Msg
showSelector model =
  select
    [ onInput ShowWasChosen
    , style ["margin-left"=>"0px"]
    , attribute "required" ""
    ]
    <|
    ( option
       [ attribute "value" ""
       , tagattr <| if isNothing model.selectedShow then "selected" else "dummy"
       , tagattr "disabled"
       , tagattr "hidden"
       ]
       [text "Please pick a show..."]
    )
    ::
    (
      List.map
        (\show ->
          option
            [ attribute "value" (toString show.id)
            , tagattr <| case model.selectedShow of
                Just s -> if show.id == s.id then "selected" else "dummy"
                Nothing -> "dummy"
            ]
            [text show.data.title]
        )
        model.shows
    )


showDateSelector : Model -> Html Msg
showDateSelector model =
  div [style ["margin-left"=>"0px"]]
  [ (DatePicker.view
      model.selectedShowDate
      DatePicker.defaultSettings
      model.datePicker
    ) |> Html.map SetDatePicker
  ]

layout_header : Model -> List (Html Msg)
layout_header model =
  [Layout.title []
  [ Layout.row []
    [ layout_header_col_appName model
    , layout_header_col_trackInfo model
    , layout_header_col_showInfo model
    ]
  ]
  ]


layout_header_col_appName : Model -> Html Msg
layout_header_col_appName model =
  div [style ["font-size"=>"20pt", "margin-right"=>"50px"]]
    [ span [style ["margin-right"=>"8px"]] [text "🎶 "]
    , text "DJ Ops"
    ]


timeRemaining min sec =
  let
    min0 = if String.length min < 2 then "0"++min else min
    sec0 = if String.length sec < 2 then "0"++sec else sec
    digitStyle = style
      [ "font-family"=>"'Share Tech Mono', monospace"
      , "letter-spacing"=>"-3px"
      ]
    colonStyle = style
      [ "margin-right"=>"-2px"
      , "margin-bottom"=>"3px"
      ]
  in
    div [style ["display"=>"inline-block", "vertical-align"=>"bottom", "padding-left"=>"3px", "padding-right"=>"3px", "margin-right"=>"10px", "font-size"=>"26pt", "border"=>"solid white 1px"]]
    [ span [digitStyle] [ text min0 ]
    , span [colonStyle] [ text ":" ]
    , span [digitStyle] [ text sec0 ]
    ]


stackedPair name1 val1 name2 val2 =
  let
    colonize s = text <| s ++ ": "
    italicize s = i [] [text s]
    theStyle = style
      [ "display"=>"inline-block"
      , "vertical-align"=>"bottom"
      , "font-size"=>"14pt"
      ]
  in
    div [theStyle]
    [ span [style ["margin-top"=>"4px"]]
      [ colonize name1, italicize val1
      , br [] []
      , colonize name2, italicize val2
      ]
    ]

dashes = "--"
dots = "..."

layout_header_col_trackInfo : Model -> Html Msg
layout_header_col_trackInfo model =
  let
    titleLabel = "Title"
    artistLabel = "Artist"
    blankInfo = [ timeRemaining dashes dashes, stackedPair titleLabel dots artistLabel dots]
    divStyle =
      style
      [ "width"=>"450px"
      , "white-space"=>"nowrap"
      , "overflow"=>"hidden"
      , "text-overflow"=>"ellipsis"
      , "margin-right"=>"50px"
      ]
  in div [divStyle]
    (
    case model.nowPlaying of
      Just {track} ->
        (
          case track of
            Just t ->
              if t.remainingSeconds > 0 then
                [ timeRemaining
                    (toString <| floor <| t.remainingSeconds/60)
                    (toString <| rem (floor t.remainingSeconds) 60)
                , stackedPair titleLabel t.title artistLabel t.artist
                ]
              else
                blankInfo

            Nothing ->
              blankInfo
        )

      Nothing ->
        blankInfo
    )

layout_header_col_showInfo : Model -> Html Msg
layout_header_col_showInfo model =
  let
    showLabel = "Show"
    hostLabel = "Host"
    blankInfo = [timeRemaining dashes dashes, stackedPair showLabel dots hostLabel dots]
  in div [style ["width"=>"450px", "white-space"=>"nowrap", "overflow"=>"hidden", "text-overflow"=>"ellipsis"]]
    (
    case model.nowPlaying of
      Just {show} ->
        (
          case show of
            Just s ->
              if s.remainingSeconds > 0 then
                [ timeRemaining
                    (toString <| floor <| s.remainingSeconds/60)
                    (toString <| rem (floor s.remainingSeconds) 60)
                , stackedPair showLabel s.title hostLabel (String.join " & " s.hosts)
                ]
              else
                blankInfo

            Nothing ->
              blankInfo
        )

      Nothing ->
        blankInfo
    )

layout_main : Model -> Html Msg
layout_main model =
  case model.selectedTab of
    0 ->
      tab_start model
    1 ->
      tab_tracks model
    _ ->
      p [] [text <| "Tab " ++ toString model.selectedTab ++ " not yet implemented."]


tab_start : Model -> Html Msg
tab_start model =
  let
    numTd isSet = td [style ["padding-left"=>"5px", "font-size"=>"24pt", "color"=>(if isSet then "green" else "red")]]
    instTd = td [style ["padding-left"=>"15px"]]
    checkTd = td []
    para = p [style ["margin-top"=>"10px"]]
    row = tr []
    break = br [] []
  in
    div [style ["margin"=>"30px", "zoom"=>"1.3"]]
    [ p [] [text "Welcome to the DJ Ops Console!"]
    , table []
      [ row
        [ numTd (isJust model.userid && isJust model.password && isJust model.member) [text "❶ "]
        , instTd
          [ para
            [ input
                [ attribute "placeholder" "userid"
                , attribute "value" <| withDefault "" model.userid
                , onInput UseridInput
                ]
                []
            , break
            , input
                [ style ["margin-top"=>"3px"]
                , attribute "placeholder" "password"
                , attribute "type" "password"
                , attribute "value" <| withDefault "" model.password
                , onInput PasswordInput
                ]
                []
            , Button.render Mdl [0] model.mdl
              [ css "position" "relative"
              , css "bottom" "20px"
              , css "margin-left" "10px"
              , Button.raised
              , Button.colored
              , Button.ripple
              , Opts.onClick Login_Clicked
              ]
              [ text "Login"]
            ]
          ]
        ]
      , row
        [ numTd (isJust model.selectedShow) [text "❷ "]
        , instTd [para [text "Choose a show to work on: ", br [] [], showSelector model]]
        ]
      , row
        [ numTd (isJust model.selectedShowDate) [text "❸ "]
        , instTd [para [text "Specify the show date: ", showDateSelector model]]
        ]
      , row
        [ numTd False [span [style ["color"=>"green"]] [text "❹ "]]
        , instTd
          [ para
            [ text "ONLY when it's time to start your LIVE show:"
            , br [] []
            , Button.render Mdl [0] model.mdl
              [ Button.raised
              , Button.colored
              , Button.ripple
              -- TODO: test, below, should also be true if today is NOT show date.
              , if isNothing model.selectedShow || isNothing model.member || isNothing model.selectedShowDate then
                  Button.disabled
                else case model.selectedShowDate of
                  Just ssd ->
                    if CD.fromDate ssd /= CD.fromTime model.currTime then Button.disabled else Opts.nop
                  Nothing ->
                    Button.disabled
              --, Opts.onClick MyClickMsg
              ]
              [ text "Begin Broadcast!"]
            ]
          ]
        ]
      ]
    ]


tab_tracks : Model -> Html Msg
tab_tracks model =
  div []
    [ tracks_info model
    , tracks_table model
    ]


tracks_info : Model -> Html Msg
tracks_info model =
  div
    [ style
      [ "float"=>"right"
      , "position"=>"fixed"
      , "right"=>"50px"
      , "top"=>"150px"
      , "font-size"=>"16pt"
      ]
    ]
    [ p [style ["font-size"=>"16pt"]]
      ( case (model.selectedShow, model.selectedShowDate) of
        (Just show, Just date) ->
          [ text "🡄"
          , br [] []
          , text "Tracks for"
          , br [] []
          , text show.data.title
          , br [] []
          , text (date |> CD.fromDate |> CD.format "%a, %b %ddd")
          ]
        _ ->
          [ text "Finish the START tab."
          ]
      )
    ]

tracks_table : Model -> Html Msg
tracks_table model =
  Table.table [css "margin" "20px"]
    [ Table.tbody []
      (List.map (tracks_tableRow model) (List.range 1 numTrackRows))
    ]


tracks_tableRow : Model -> Int -> Html Msg
tracks_tableRow model r =
  let
    aTd s tte c opts =
      Table.td restTdStyle
        [Textfield.render
          Mdl
          [tracksTabId, r, c]  -- Textfield ID
          model.mdl
          ( opts
            ++
            [ Textfield.label s
            , Textfield.value <|
                if c == artistColId then tte.artist
                else if c == titleColId then tte.title
                else if c == durationColId then tte.duration
                else "ERR1" -- TODO: Note unexpected situation?
            , Opts.onInput (TrackFieldUpdate r c)
            ]
          )
          []
        ]
  in
    case Array.get r model.tracksTabEntries of
      Just tte ->
        Table.tr [css "color" (if isNothing tte.lastChanged then "black" else "red")]
        [ Table.td firstTdStyle [text <| toString r]
        , aTd "Artist" tte artistColId []
        , aTd "Title" tte titleColId []
        , aTd "MM:SS" tte durationColId [css "width" "55px"]
        , Table.td firstTdStyle
          [ Button.render Mdl [r] model.mdl
            [ Button.fab
            , Button.plain
            -- , Options.onClick MyClickMsg
            ]
            [ Icon.i "play_arrow"]
          ]
        ]
      Nothing ->
        -- TODO: Log this unexpected situation?
        Table.tr [] []



-----------------------------------------------------------------------------
-- SUBSCRIPTIONS
-----------------------------------------------------------------------------

subscriptions : Model -> Sub Msg
subscriptions model =
  Sub.batch
    [ Time.every second Tick
    , Keyboard.downs KeyDownRfid
    , Layout.subs Mdl model.mdl
    ]


-----------------------------------------------------------------------------
-- UTILITIES
-----------------------------------------------------------------------------

-- From https://stackoverflow.com/questions/40599512/how-to-achieve-behavior-of-settimeout-in-elm
delay : Time.Time -> msg -> Cmd msg
delay time msg = Process.sleep time |> Task.perform (\_ -> msg)


-----------------------------------------------------------------------------
-- STYLES
-----------------------------------------------------------------------------

(=>) = (,)

userIdPwInputStyle =
  style
  [ "margin-left" => "50px"
  ]

firstTdStyle =
  [ css "border-style" "none"
  , css "color" "gray"
  , css "font-size" "26pt"
  , css "font-weight" "bold"
  ]

restTdStyle =
  [ css "border-style" "none"
  , css "padding-top" "0"
  ]


-----------------------------------------------------------------------------
-- RFID
-----------------------------------------------------------------------------

-- Example of RFID data: ">0C00840D"
-- ">" indicates start of data. It is followed by 8 hex characters.
-- "0C00840D" is the big endian representation of the ID

delimitedRfidNum = Regex.regex ">[0-9A-F]{8}"
rfidCharsOnly = Regex.regex "^>[0-9A-F]*$"


checkAnRfid : Model -> (Model, Cmd Msg)
checkAnRfid model =
  case model.state of

    CheckingAnRfid _ ->
      -- We only check one at a time, and a check is already in progress, so do nothing.
      (model, Cmd.none)

    HitAnHttpErr _ ->
      -- We probably shouldn't even get here. Do nothing, since the error kills any progress.
      (model, Cmd.none)

    FoundRfidToBe _ ->
      -- We probably shouldn't even get here. Do nothing.
      (model, Cmd.none)

    Nominal ->
      -- We'll check the first one on the list, if it's non-empty.
      case model.rfidsToCheck of

        rfid :: rfids ->
          let
            newModel = {model | rfidsToCheck=rfids, state=CheckingAnRfid 0}
            memberFilters = [XisApi.RfidNumberEquals rfid]
            listCmd = model.xis.listMembers memberFilters MemberListResult
          in
            (newModel, listCmd)

        [] ->
          -- There aren't any ids to check. Everything we've tried has failed.
          ({model | state=FoundRfidToBe False}, Cmd.none)


rfid_dialog_config : Model -> Maybe (Dialog.Config Msg)
rfid_dialog_config model =

  case model.state of

    Nominal ->
      Nothing

    FoundRfidToBe True ->
      Nothing

    _ ->
      Just
        { closeMessage = Just AcknowledgeDialog
        , containerClass = Nothing
        , containerId = Nothing
        , header = Just (text "🎶 RFID Check-In")
        , body = Just (rfid_dialog_body model)
        , footer = Nothing
        }


rfid_dialog_body : Model -> Html Msg
rfid_dialog_body model =

  case model.state of

    CheckingAnRfid waitCount ->
      p []
        [ text "One moment while we check our database."
        , text (String.repeat waitCount "●")
        ]

    FoundRfidToBe False ->
      p []
        [ text "Couldn't find your RFID in our database."
        , br [] []
        , text "Tap the BACK button and try again or"
        , br [] []
        , text "speak to a staff member for help."
        ]

    HitAnHttpErr e ->
      p []
        [ text "Tap the BACK button and try again or"
        , br [] []
        , text "speak to a staff member for help."
        ]

    _ -> text ""


-----------------------------------------------------------------------------
-- UTILITY
-----------------------------------------------------------------------------
