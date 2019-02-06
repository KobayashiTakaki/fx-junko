#!/bin/sh
pid=$(ps ax | grep python | grep scheduler | awk '{print $1}')
kill $pid
nohup python scheduler.py &
exit
