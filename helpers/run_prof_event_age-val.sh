#!/bin/bash

if [ ! -x "trim" ] ; then
   echo "No trim found. Change to the right dir first"
   exit 1
fi

MOD_CONF_DIR="../lib/models/event_age/etc"
/bin/cp -af ${MOD_CONF_DIR}/m_config.yaml ${MOD_CONF_DIR}/m_config.yaml.ref || exit 1

if [ -z "$1" ] ; then
   TRIM_C='0.7'
else
   TRIM_C="$1"
fi
DEF_OUT_DIR="../output"
OUT_DIR="../../prod/output/results/val/event_age/${TRIM_C}"
if [ ! -d "${OUT_DIR}" ] ; then
   echo "Creating output dir ${OUT_DIR}"
   mkdir -p ${OUT_DIR} || exit 1
fi

for j in delta0 delta1 normal uniform astride ; do
   sed -e "s/proc: .*$/proc: '${j}'/g" ${MOD_CONF_DIR}/m_config.yaml.ref \
          > ${MOD_CONF_DIR}/m_config.yaml || exit 1
   grep "proc:" ${MOD_CONF_DIR}/m_config.yaml
   for k in total ; do
      for i in 0 m d s x ; do
         echo "dataset = history_scram-${i}f   strategy = ${k}  procedure = ${j}"
         mkdir -p ${OUT_DIR}/history_scram-${i}f/${k}/${j} || exit 1

         echo "trim -v1 -i history_scram-${i}f.csv -t 'updated' -c ${TRIM_C} " \
               > run_history_scram-${i}f_${k}_${j}-val.log
         echo "     -m event_age -s ${k} -p -e -x 'value'" \
               >> run_history_scram-${i}f_${k}_${j}-val.log         
         ./trim -v1 -i history_scram-${i}f.csv -t 'updated' -c ${TRIM_C} -x 'value' \
                 -m event_age -s ${k} -p -e >> run_history_scram-${i}f_${k}_${j}-val.log

         mv run_history_scram-${i}f_${k}_${j}-val.log \
            ${OUT_DIR}/history_scram-${i}f/${k}/${j}/ || exit 1
         mv ${DEF_OUT_DIR}/history_scram-${i}f_event_age_*_${k}* \
            ${OUT_DIR}/history_scram-${i}f/${k}/${j}/

      done
   done
done

/bin/mv -f ${MOD_CONF_DIR}/m_config.yaml.ref ${MOD_CONF_DIR}/m_config.yaml
 
