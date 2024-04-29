/*
 Given an MRN and a time-window in which to search return the value of
 a particular observation type for a patient. For example, this observation type
 could be a height, weight or GCS (Glasgow coma scale) value
 */
set search_path to ${{ schema_name }},public;

select
  vo.value_as_real

from core_demographic
join hospital_visit as hv using(mrn_id)
join visit_observation as vo using(hospital_visit_id)
join mrn using(mrn_id)
join visit_observation_type as vot
on vo.visit_observation_type_id = vot.visit_observation_type_id
    and vot.name = :observation_type

where mrn.mrn = :mrn
    and vo.observation_datetime >= :window_start
    and vo.observation_datetime < :window_end

order by greatest(vo.observation_datetime - :window_midpoint,
  :window_midpoint - vo.observation_datetime) -- abs(time difference)
limit 1