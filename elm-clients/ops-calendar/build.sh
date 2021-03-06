#!/usr/bin/env bash

set -x

ELM=src/OpsCalendar.elm
JS=out/OpsCalendar.js
MIN=../../tasks/static/tasks/OpsCalendar.min.js

#if elm-make --yes ${ELM} --output=${JS} && cat ${JS} > ${MIN}
if elm-make --yes ${ELM} --output=${JS} && minify ${JS} > ${MIN}
#if elm-make --debug --yes ${ELM} --output=${JS} && minify ${JS} > ${MIN}
then
    sed -i "1i// Generated by Elm" ${JS}
    sed -i "1i// Generated by Elm" ${MIN}
fi

paplay /usr/share/sounds/ubuntu/stereo/dialog-information.ogg

