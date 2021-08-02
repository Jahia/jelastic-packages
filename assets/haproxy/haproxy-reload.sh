#!/usr/bin/bash
HAPROXY_CFG="/etc/haproxy/haproxy.cfg"
output=$(service haproxy reload 2>&1)
if [[ $? -eq 0 ]]; then
    exit 0
fi

# create/populate custom files arrays for mapping purpose
# 2 arrays are created:
# - files: name of the customer's conf file
# - lines: line where the customer's conf file start in HAPROXY_CFG
eval "$(awk '/^## CUSTOMER_FILENAME/ \
             { \
                 line=NR; \
                 n=split($NF,path,"/"); \
                 file=path[n]; \
                 printf "lines+=(%s); files+=(%s)\n",line,file \
             }' \
             $HAPROXY_CFG)"

while read -r error; do                                            # For each "parsing" error on haproxy reload:
  l=$(echo "$error" | sed -E 's/^.+\[.+:([[:digit:]]+)\].+$/\1/')  # we extract the linue number in HAPROXY_CFG,
  errormsg+=("$(echo $error | cut -d':' -f 4-)")                   # and we create/populate a errormsg array.
  for f in ${!lines[@]}; do                                        # Then for each mapped customer's conf files:
    bottom=${lines[$f]}                                            # we get the range a customer's file with the start line
    upper=${lines[$f+1]}                                           # and the start of the next file (if any).
    if (( ($f+1) != ${#lines[@]} )); then                          # We check here if another file is following the current or not:
      if (( $bottom < $l && $l < $upper )); then                   # if yes, then we test if the $l is in the file range:
        line+=($(echo "$l - $bottom" | bc))                        # if yes we create/populate a line array with the customer's file relative line,
        file+=(${files[$f]})                                       # a file array with the name of the file,
        break                                                      # then we break the for loop and go to the next error if any.
      fi
    else                                                           # If there is no following customer's file after the current one:
      if (( $bottom < $l )); then                                  # we test if the $l is beyond the file start line number:
        line+=($(echo "$l - $bottom" | bc))                        # if yes we create/populate a line array with the customer's file relative line,
        file+=(${files[$f]})                                       # and a a file array with the name of the file.
      fi
    fi
  done
done < <(echo "$output" | grep " parsing ")


# We check we got "parsing" error
# because if not, then we have another problem here
if (( ${#file[@]} == 0 )); then
  echo "HAProxy error(s) is not due to parsing error, see stderr for details."
  echo "$output" 1>&2
  exit 200
fi


# For having a json ouput in a easy way for the front,
# we generate a csv style output like this:
# <file name> → <relative line number>: <error message from haproxy output>
# each line is stored in an array
n=0
for f in ${file[@]}; do
  hihi+=("${f} → ${line[$n]}:${errormsg[$n]}")
  ((n++))
done
# Then we replay the previous array
# by sending each item to jq in order
# to construct a json
for ((i=0; i<${#hihi[@]}; i++)); do
  echo ${hihi[$i]} 
done | jq -cMRrn 'reduce inputs as $line
                  ( {}
                  ; ($line | split(" → ")) as $elements
                  | . [$elements[0]] += 
                    [ $elements[1]
                    ]
                  )' 1>&2
exit 100
