#!/bin/bash

if [ ! -x "trim" ] ; then
   echo "No trim found. Change to the right dir first"
   exit 1
fi

MODEL='event_time_resolution'
MOD_CONF_DIR="../lib/models/${MODEL}/etc"
/bin/cp -af ${MOD_CONF_DIR}/m_config.yaml ${MOD_CONF_DIR}/m_config.yaml.ref || exit 1

TRIM_LIMITS="${MOD_CONF_DIR}/trim-limits"
DEF_OUT_DIR="../output"

#for j in delta0 delta1 normal uniform astride ; do
for j in astride delta0 normal uniform ; do
   sed -e "s/proc: .*$/proc: '${j}'/g" ${MOD_CONF_DIR}/m_config.yaml.ref \
          > ${MOD_CONF_DIR}/m_config.yaml || exit 1
   T1=$(grep "proc:" ${MOD_CONF_DIR}/m_config.yaml)
   echo "${MODEL}  ${T1}"
   #for k in total block event ; do
   for k in block event ; do
      for i in 0 m d s x ; do
	TRIM_N=$( grep history_scram-${i}f.csv ${TRIM_LIMITS} | awk '{print $3}' )
	RES_DIR="../../results/${MODEL}/history_scram-${i}f/${TRIM_N}/${k}/${j}"
        if [ ! -d "${RES_DIR}" ] ; then
           echo "Creating output dir ${RES_DIR}"
           mkdir -p ${RES_DIR} || exit 1
        fi

        echo "dataset = history_scram-${i}f   strategy = ${k}  procedure = ${j}  trim = ${TRIM_N}"

        echo "trim -v1 -i history_scram-${i}f.csv -t 'updated' -n ${TRIM_N}" \
              > ${RES_DIR}/run_history_scram-${i}f_${k}_${j}.log
        echo "     -m ${MODEL} -s ${k} -p -e" \
              >> ${RES_DIR}/run_history_scram-${i}f_${k}_${j}.log         
        ./trim -v1 -i history_scram-${i}f.csv -t 'updated' -n ${TRIM_N} \
                -m ${MODEL} -s ${k} -p -e >> ${RES_DIR}/run_history_scram-${i}f_${k}_${j}.log

        mv ${DEF_OUT_DIR}/history_scram-${i}f_${MODEL}_*_${k}* ${RES_DIR}/

      done
   done
done

/bin/mv -f ${MOD_CONF_DIR}/m_config.yaml.ref ${MOD_CONF_DIR}/m_config.yaml
 
