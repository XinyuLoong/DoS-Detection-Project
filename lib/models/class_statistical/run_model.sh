#!/bin/bash

CLI_SCRIPT_PATH="${BASH_SOURCE[0]}"
SCRIPT_PATH=$(readlink -f "${CLI_SCRIPT_PATH}")
SCRIPT_DIR=$(dirname "$SCRIPT_PATH")
MODEL_NAME=$(basename "$SCRIPT_DIR")

if [ ! -x "t_model" ] ; then
   echo "No t_model found. Change to the right dir first"
   exit 1
fi

MOD_CONF_DIR="etc"
/bin/cp -af ${MOD_CONF_DIR}/m_config.yaml ${MOD_CONF_DIR}/m_config.yaml.ref || exit 1

if [ -z "$1" ] ; then
   TRIM_C='0.7'
else
   TRIM_C="$1"
fi
DEF_OUT_DIR="../../../output"
OUT_DIR="../../../../prod/output/results/${MODEL_NAME}/${TRIM_C}"
if [ ! -d "${OUT_DIR}" ] ; then
   echo "Creating output dir ${OUT_DIR}"
   mkdir -p ${OUT_DIR} || exit 1
fi

#for j in delta0 delta1 normal uniform astride ; do
for j in astride ; do
   sed -e "s/proc: .*$/proc: '${j}'/g" ${MOD_CONF_DIR}/m_config.yaml.ref \
          > ${MOD_CONF_DIR}/m_config.yaml || exit 1
   grep "proc:" ${MOD_CONF_DIR}/m_config.yaml
   for k in total block event ; do
      for i in 0 m d s x ; do
         echo "dataset = history_scram-${i}f   strategy = ${k}  procedure = ${j}"
         mkdir -p ${OUT_DIR}/history_scram-${i}f/${k}/${j} || exit 1
         
         echo "t_model -v0 -i history_scram-${i}f.csv -t 'updated' -c ${TRIM_C} -s ${k}" \
            >> time_history_scram-${i}f_${k}_${j}.log
         ( time ./t_model -v0 -i history_scram-${i}f.csv -t 'updated' -c ${TRIM_C} -s ${k}) \
            2> time_history_scram-${i}f_${k}_${j}.log
         
         /bin/mv -f time_history_scram-${i}f_${k}_${j}.log \
            ${OUT_DIR}/history_scram-${i}f/${k}/${j}/ || exit 1
         rmdir ${DEF_OUT_DIR}/history_scram-${i}f_${MODEL_NAME}_*_${k}* 
         
      done
   done
done

/bin/mv -f ${MOD_CONF_DIR}/m_config.yaml.ref ${MOD_CONF_DIR}/m_config.yaml
 
