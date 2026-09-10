#!/bin/bash

if [ ! -x "trim" ] ; then
   echo "No trim found. Change to the right dir first"
   exit 1
fi

MODEL='event_statistical'
MOD_CONF_DIR="../lib/models/${MODEL}/etc"
/bin/cp -af ${MOD_CONF_DIR}/m_config.yaml ${MOD_CONF_DIR}/m_config.yaml.ref || exit 1

if [ -z "$1" ] ; then
   TRIM_C='0.99'
else
   TRIM_C="$1"
fi

DEF_OUT_DIR="../output"
OUT_DIR="../../results/${MODEL}"
if [ ! -d "${OUT_DIR}" ] ; then
   echo "Creating output dir ${OUT_DIR}"
   mkdir -p ${OUT_DIR} || exit 1
fi

#for j in delta0 delta1 normal uniform astride ; do
for j in astride delta0 uniform normal ; do
   sed -e "s/proc: .*$/proc: '${j}'/g" ${MOD_CONF_DIR}/m_config.yaml.ref \
          > ${MOD_CONF_DIR}/m_config.yaml || exit 1
   T1=$(grep "proc:" ${MOD_CONF_DIR}/m_config.yaml)
   echo "${MODEL}  ${T1}"
   #for k in total block event ; do
   for k in block event ; do
      for i in 0 m d s x ; do
         RES_DIR="${OUT_DIR}/history_scram-${i}f/${j}/${k}"
         echo "dataset = history_scram-${i}f   strategy = ${k}  procedure = ${j}  trim = ${TRIM_C}"
         if [ ! -d "${RES_DIR}" ] ; then
            mkdir -p ${RES_DIR} || exit 1
         fi

         echo "trim -v1 -i history_scram-${i}f.csv -t 'updated' -c ${TRIM_C}" \
               > ${RES_DIR}/run_history_scram-${i}f_${k}_${j}.log
         echo "     -m ${MODEL} -s ${k} -p -e" \
               >> ${RES_DIR}/run_history_scram-${i}f_${k}_${j}.log         
         ./trim -v1 -i history_scram-${i}f.csv -t 'updated' -c ${TRIM_C} \
                 -m ${MODEL} -s ${k} -p -e >> ${RES_DIR}/run_history_scram-${i}f_${k}_${j}.log

         mv ${DEF_OUT_DIR}/history_scram-${i}f_${MODEL}_*_${k}* \
            ${RES_DIR}/

      done
   done
done

/bin/mv -f ${MOD_CONF_DIR}/m_config.yaml.ref ${MOD_CONF_DIR}/m_config.yaml
 
