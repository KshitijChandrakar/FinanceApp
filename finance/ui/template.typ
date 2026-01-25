
#let subtitle(b) = [
  #for i in b [
    == #i.at(0)
    #for j in i.at(1) [
      *#j.at(0)*... #j.at(1) \
    ]
  ]
]

#subtitle(json("summary.json"))
