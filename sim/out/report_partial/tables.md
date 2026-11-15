## Overall (T6 and T9 excluded from success_nav)

| sim      | config    |   episodes | success_nav   |   SPL | wrong_target   |   collisions |   min_clearance |   lat_med_ms |
|:---------|:----------|-----------:|:--------------|------:|:---------------|-------------:|----------------:|-------------:|
| pybullet | C0 Oracle |         75 | 100% [95-100] |  0.99 | 0% [0-5]       |            0 |            0.14 |          0.4 |

## Per scenario

| sim      | config   | scenario   |   n | success       |   SPL |   t_success_med_s |   dist_err_med_m | wrong_target   | collision_runs   | min_clear_m(min/med)   |   interventions_mean |   lat_perc_med_ms |   lat_perc_p95_ms |
|:---------|:---------|:-----------|----:|:--------------|------:|------------------:|-----------------:|:---------------|:-----------------|:-----------------------|---------------------:|------------------:|------------------:|
| pybullet | C0       | T1         |  20 | 100% [84-100] |  1    |              14.4 |            0.044 | 0% [0-16]      | 0% [0-16]        | 0.49/0.58              |                  0   |               0.4 |               0.5 |
| pybullet | C0       | T2         |  20 | 100% [84-100] |  1    |              16.7 |            0.03  | 0% [0-16]      | 0% [0-16]        | 0.39/0.82              |                  0   |               0.3 |               0.4 |
| pybullet | C0       | T3         |  20 | 100% [84-100] |  0.97 |              34.6 |            0.04  | 0% [0-16]      | 0% [0-16]        | 0.14/0.36              |                  2.8 |               0.3 |               0.5 |
| pybullet | C0       | T4         |  15 | 100% [80-100] |  0.99 |              15.9 |            0.019 | 0% [0-20]      | 0% [0-20]        | 0.19/0.37              |                  2.3 |               0.4 |               0.5 |

## Command parser (P4): 100% of 30 phrasings correct

| command                                        | expected    | expect_clarify   | got         | clarify                                                                 | intent        | correct   |
|:-----------------------------------------------|:------------|:-----------------|:------------|:------------------------------------------------------------------------|:--------------|:----------|
| find and approach the orange                   | orange      | False            | orange      | nan                                                                     | find_approach | True      |
| go to the orange                               | orange      | False            | orange      | nan                                                                     | find_approach | True      |
| fly near the orange and stop half a metre away | orange      | False            | orange      | nan                                                                     | find_approach | True      |
| locate the orange fruit                        | orange      | False            | orange      | nan                                                                     | find_approach | True      |
| can you find the orange for me                 | orange      | False            | orange      | nan                                                                     | find_approach | True      |
| approach the orange, stay 50 cm away           | orange      | False            | orange      | nan                                                                     | find_approach | True      |
| search for an orange in the room               | orange      | False            | orange      | nan                                                                     | find_approach | True      |
| look for the oranges                           | orange      | False            | orange      | nan                                                                     | find_approach | True      |
| get close to the orange slowly                 | orange      | False            | orange      | nan                                                                     | find_approach | True      |
| fly towards the orange carefully               | orange      | False            | orange      | nan                                                                     | find_approach | True      |
| find the apple                                 | apple       | False            | apple       | nan                                                                     | find_approach | True      |
| go to the lemon and stop 1 m away              | lemon       | False            | lemon       | nan                                                                     | find_approach | True      |
| approach the orange ball                       | orange ball | False            | orange ball | nan                                                                     | find_approach | True      |
| find the orange cube                           | orange cube | False            | orange cube | nan                                                                     | find_approach | True      |
| find the orange next to the apple              | orange      | False            | orange      | nan                                                                     | find_approach | True      |
| go to the orange on the table                  | orange      | False            | orange      | nan                                                                     | find_approach | True      |
| find the orange or the apple                   | nan         | True             | orange      | Several objects mentioned (orange, apple). Which one should I approach? | find_approach | True      |
| approach the apple and the lemon               | nan         | True             | apple       | Several objects mentioned (apple, lemon). Which one should I approach?  | find_approach | True      |
| go over there                                  | nan         | True             | nan         | I did not understand the task. Should I find and approach an object?    | nan           | True      |
| find it                                        | nan         | True             | nan         | Which object should I find?                                             | find_approach | True      |
| do a flip                                      | nan         | True             | nan         | I did not understand the task. Should I find and approach an object?    | nan           | True      |
| orange                                         | nan         | True             | orange      | I did not understand the task. Should I find and approach an object?    | nan           | True      |
| stop                                           | nan         | False            | nan         | nan                                                                     | abort         | True      |
| land now                                       | nan         | False            | nan         | nan                                                                     | abort         | True      |
| find the orange and stay 2 metres away         | orange      | False            | orange      | nan                                                                     | find_approach | True      |
| approach the orange at 30 cm                   | orange      | False            | orange      | nan                                                                     | find_approach | True      |
| find the fruit                                 | nan         | True             | nan         | Which object should I find?                                             | find_approach | True      |
| fly to the orange thing                        | orange      | False            | orange      | nan                                                                     | find_approach | True      |
| locate the citrus                              | nan         | True             | nan         | Which object should I find?                                             | find_approach | True      |
| go find me an orange please                    | orange      | False            | orange      | nan                                                                     | find_approach | True      |
