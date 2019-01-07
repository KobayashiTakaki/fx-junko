#!/bin/sh
if [ $(ps ax | grep python | grep scheduler | wc -l) -lt 1 ]; then
  nohup python test_scheduler.py &
  exit
fi
