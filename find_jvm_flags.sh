#!/bin/env bash

"${JAVA_HOME}"/bin/java -XX:+PrintFlagsFinal -version | grep -E "InitialHeapSize|MaxHeapSize|ThreadStackSize|VMThreadStackSize"

