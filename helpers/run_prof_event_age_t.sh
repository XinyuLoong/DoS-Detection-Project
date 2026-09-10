#!/bin/bash

if [ ! -x "trim" ] ; then
   echo "No trim found. Change to the right dir first"
   exit 1
fi

MODEL='event_age'
MOD_CONF_DIR="../lib/models/${MODEL}/etc"
/bin/cp -af ${MOD_CONF_DIR}/m_config.yaml ${MOD_CONF_DIR}/m_config.yaml.ref || exit 1

DEF_OUT_DIR="../output"
OUT_DIR="../../results/${MODEL}"
if [ ! -d "${OUT_DIR}" ] ; then
   echo "Creating output dir ${OUT_DIR}"
   mkdir -p ${OUT_DIR} || exit 1
fi


for t in 0.11 0.22 0.33 0.44 0.55 0.66 0.77 0.88 0.99 ; do
for j in delta0 delta1 normal uniform astride ; do
   sed -e "s/proc: .*$/proc: '${j}'/g" ${MOD_CONF_DIR}/m_config.yaml.ref \
          > ${MOD_CONF_DIR}/m_config.yaml || exit 1
   T1=$(grep "proc:" ${MOD_CONF_DIR}/m_config.yaml)
   echo "${MODEL}  ${T1}"
   for k in total ; do
      for i in 0 m d s x ; do
         RES_DIR="${OUT_DIR}/history_scram-${i}f/${j}/${k}/${t}"
         echo "dataset = history_scram-${i}f   strategy = ${k}  procedure = ${j}  trim = ${t}"
	 if [ ! -d "${RES_DIR}" ] ; then
            mkdir -p ${RES_DIR} || exit 1
	 fi
         echo "trim -v1 -i history_scram-${i}f.csv -t 'updated' -c ${t}" \
               > ${RES_DIR}/run_history_scram-${i}f_${k}_${j}.log
         echo "     -m ${MODEL} -s ${k} -p -e" \
               >> ${RES_DIR}/run_history_scram-${i}f_${k}_${j}.log         
         ./trim -v1 -i history_scram-${i}f.csv -t 'updated' -c ${t} \
                 -m ${MODEL} -s ${k} -p -e >> ${RES_DIR}/run_history_scram-${i}f_${k}_${j}.log

         mv ${DEF_OUT_DIR}/history_scram-${i}f_${MODEL}_*_${k}* \
            ${RES_DIR}/

      done
   done
done
done

/bin/mv -f ${MOD_CONF_DIR}/m_config.yaml.ref ${MOD_CONF_DIR}/m_config.yaml
 
