# Booklet Corpus Rules

Derived from 266 accessible liturgy-related Google Docs in Drive.

## Corpus Inventory
- `reading_program`: 81
- `ordinary_time`: 66
- `epiphany`: 29
- `easter`: 29
- `lent`: 22
- `advent`: 17
- `christmas`: 11
- `palm_sunday`: 6
- `pentecost`: 5

## Family Rules
### reading_program
- Docs analyzed: 81
- Required blocks: `gathering_in_the_name_of_jesus`
- Common variants: `transfiguration` (1)
- Common title markers: `family` (4), `baptism` (3), `eve` (2), `kod` (2), `intro` (2), `general` (2), `sponsors` (2), `all` (2)
- Rule: reading programs are scripture-reader artifacts, not the main service booklet.

### ordinary_time
- Docs analyzed: 66
- Required blocks: `collect_for_today, doxology, gathering_of_the_community, peace, prayers_of_the_people, readings, summary_of_the_law, welcome, announcements, gathering_in_the_name_of_jesus, sermon, service_title, preparation_of_the_gifts`
- Optional blocks: `affirmation_of_faith, nicene_creed`
- Common variants: `kingdom_of_dallas` (7), `proper` (1)
- Common title markers: `fall` (1), `kickoff` (1), `back` (1), `to` (1), `school` (1), `father's` (1)
- Rule: start from the standard leader-booklet order with collect, readings, affirmation/creed, prayers, peace, and offertory flow.

### easter
- Docs analyzed: 29
- Required blocks: `announcements, doxology, gathering_in_the_name_of_jesus, peace, sermon, welcome, prayers_of_the_people, collect_for_today, gathering_of_the_community, preparation_of_the_gifts, readings`
- Optional blocks: `affirmation_of_faith, summary_of_the_law`
- Common title markers: `baptism` (3), `outdoor` (2), `mother's` (1), `agnus` (1), `dei` (1), `slmd` (1), `launch` (1)
- Rule: Easter should be its own family; do not assume Lent or ordinary-time penitential order.

### epiphany
- Docs analyzed: 29
- Required blocks: `affirmation_of_faith, announcements, collect_for_today, doxology, gathering_of_the_community, peace, prayers_of_the_people, readings, sermon, welcome, summary_of_the_law, preparation_of_the_gifts, gathering_in_the_name_of_jesus`
- Optional blocks: `remember_to_return_music_stand`
- Common variants: `world_mission_sunday` (2), `incarnation_sunday` (1), `inclement_weather` (1), `morning_prayer` (1), `transfiguration` (1)
- Common title markers: `world` (2), `mission` (2), `incarnation` (1), `morning` (1), `prayer` (1), `inclement` (1), `weather` (1), `transfiguration` (1)
- Rule: Epiphany is close to ordinary time structurally but carries local variants like inclement-weather and mission/incarnation overlays.

### lent
- Docs analyzed: 22
- Required blocks: `affirmation_of_faith, announcements, doxology, peace, prayers_of_the_people, readings, sermon, summary_of_the_law, welcome, acclamation, collect_for_today, gathering_in_the_name_of_jesus, preparation_of_the_gifts, service_title`
- Optional blocks: `remember_to_return_music_stand`
- Common variants: `alternative_liturgy` (2)
- Common title markers: `alternative` (2)
- Rule: Lent consistently foregrounds acclamation, penitential material, and affirmation-of-faith rather than a purely ordinary-time order.

### advent
- Docs analyzed: 17
- Required blocks: `announcements, collect_for_today, doxology, gathering_in_the_name_of_jesus, gathering_of_the_community, peace, prayers_of_the_people, readings, service_title, summary_of_the_law, welcome, nicene_creed, sermon`
- Optional blocks: `preparation_of_the_gifts`
- Rule: preserve the Advent-specific gathering shape and expect Advent-title/season framing.

### christmas
- Docs analyzed: 11
- Required blocks: `doxology, peace, prayers_of_the_people, readings, service_title, welcome, gathering_in_the_name_of_jesus, gathering_of_the_community, nicene_creed, sermon`
- Optional blocks: `collect_for_today, announcements, summary_of_the_law, preparation_of_the_gifts, procession`
- Common title markers: `eve` (4)
- Rule: Christmas often adds seasonal ceremony such as wreath lighting or procession and occasionally includes `collect_for_purity`.

### palm_sunday
- Docs analyzed: 6
- Required blocks: `announcements, liturgy_of_the_palms_passion_reading_and_eucharist, peace, service_title, doxology, gathering_of_the_community, offering, palm_gospel, prayers_of_the_people, procession`
- Optional blocks: `affirmation_of_faith, prep, sermon, summary_of_the_law, childrens_dismissal, remaining_outside, the_psalm_reading, welcome, confession, lords_prayer`
- Common title markers: `slmd` (1), `preview` (1), `service` (1)
- Rule: Palm Sunday is a special liturgy with procession, outdoor start, palm gospel, and distinct prep notes.

### pentecost
- Docs analyzed: 5
- Required blocks: `peace, announcements, doxology, gathering_of_the_community, prayers_of_the_people, sermon, summary_of_the_law, welcome`
- Optional blocks: `affirmation_of_faith, collect_for_today, pentecost_sunday, preparation_of_the_gifts, readings, gathering_in_the_name_of_jesus, gathering_outdoors_in_the_name_of_jesus, new_member_presentation, offering, pentecost, preacher_and_officiant:_james_madden`
- Common title markers: `pentecost` (5), `outdoor` (3)
- Rule: Pentecost needs a seasonal overlay family even if the run of show resembles ordinary time.

## Generator Rules
- `reading_program` is a separate artifact family from the main leader booklet.
- Treat sections present in at least 75% of a family as required managed blocks.
- Treat sections present in 30%-74% of a family as optional family blocks.
- Preserve logistics and production cues as human-authored unless they are explicitly marked for management.
- Use title keywords and special-case markers like `alternative liturgy`, `kingdom of dallas`, `inclement weather`, and `world mission sunday` as variant flags layered on top of the base family.
- Palm Sunday and Passion/Holy Week style liturgies should not inherit directly from ordinary-time order.

