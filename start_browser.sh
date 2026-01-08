#!/bin/bash
"/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary" \
  --remote-debugging-port=9222 \
  --user-data-dir="/tmp/canary_dev_session" \
  --disable-backgrounding-occluded-windows \
  --disable-renderer-backgrounding \
  --disable-background-timer-throttling \
  --disable-features=CalculateNativeWinOcclusion