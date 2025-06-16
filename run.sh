today=`date -u "+%Y-%m-%d"`
cd arxiv
python paper_filter.py --path ../data/${today}.jsonl
python paper_translate.py --data ../data/${today}.jsonl
python paper2md.py --data ../data/${today}_zh.jsonl

ls data/*.jsonl | sed 's|data/||' > assets/file-list.txt