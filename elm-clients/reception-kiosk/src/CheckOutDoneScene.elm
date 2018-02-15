
module CheckOutDoneScene exposing (init, sceneWillAppear, view, CheckOutDoneModel)

-- Standard
import Html exposing (Html, div, text)
import Time exposing (Time)

-- Third Party
import Material
import List.Nonempty exposing (Nonempty)

-- Local
import Types exposing (..)
import Wizard.SceneUtils exposing (..)


-----------------------------------------------------------------------------
-- CONSTANTS
-----------------------------------------------------------------------------

displayTimeout = 5


-----------------------------------------------------------------------------
-- INIT
-----------------------------------------------------------------------------

-- This type alias describes the type of kiosk model that this scene requires.
type alias KioskModel a =
  { a
  ------------------------------------
  | mdl : Material.Model
  , flags : Flags
  , sceneStack : Nonempty Scene
  ------------------------------------
  , checkOutDoneModel : CheckOutDoneModel
  }

type alias CheckOutDoneModel =
  {
  }

init : Flags -> (CheckOutDoneModel, Cmd Msg)
init flags = ({}, Cmd.none)


-----------------------------------------------------------------------------
-- SCENE WILL APPEAR
-----------------------------------------------------------------------------

sceneWillAppear : KioskModel a -> Scene -> Scene -> (CheckOutDoneModel, Cmd Msg)
sceneWillAppear kioskModel appearing vanishing =
  if appearing == CheckOutDone
    then
      (kioskModel.checkOutDoneModel, rebase)
    else
      (kioskModel.checkOutDoneModel, Cmd.none)


-----------------------------------------------------------------------------
-- UPDATE
-----------------------------------------------------------------------------


-----------------------------------------------------------------------------
-- VIEW
-----------------------------------------------------------------------------

view : KioskModel a -> Html Msg
view kioskModel =
  let sceneModel = kioskModel.checkOutDoneModel
  in genericScene kioskModel
    "You're Checked Out"
    "Have a Nice Day!"
    (vspace 40)
    [ButtonSpec "Ok" msgForReset True]
    [] -- Never any bad news for this scene


-----------------------------------------------------------------------------
-- TICK (called each second)
-----------------------------------------------------------------------------

