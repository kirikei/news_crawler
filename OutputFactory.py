import json
import psycopg2

class OutputFactory(object):
    def __init__(self, outputType, filename = None):
        self.filename = filename
        self.outputType = outputType
        if outputType == 'db':
            self.conn = psycopg2.connect("dbname=postgres host=localhost user=admin")
            cur = self.conn.cursor()
            cur.execute("""select count(*) from pg_tables
                    where tablename='newsarticles'""")
            if (cur.fetchall())[0][0] == 0:
                cur.execute("".join(("create table newsarticles(aid text PRIMARY KEY ,",
                                                            "title text,",
                                                            "summary text,",
                                                            "link text,",
                                                            "text text,",
                                                            "media text,",
                                                            "image text,",
                                                            "pid text,",
                                                            "category text,",
                                                            "pubdate text,",
                                                            "created_at timestamp,",
                                                            "updated_at timestamp,",
                                                            "analyzed_at timestamp);")))
                self.conn.commit()

    def write(self,records):
        if self.outputType == 'stdout':
            output = lambda x: self.stdOutput(x)
        elif self.outputType == 'db':
            output = lambda x: self.sqliteOutput(x)
        elif self.outputType == 'json':
            output = lambda x: self.jsonOutput(x)

        output(records)

    def fix_format(self,rec):
        return (rec['aid'],rec['title'],rec['summary'],rec['link'],rec['text'],rec['media'],rec['img'],rec['pid'],rec['tid'],rec['publishedDate'])

    def stdOutput(self,records):
        for record in records:
            print(record)

    def jsonOutput(self,records):
        # for record in records:
            # del(record['summary'])
        with open(self.filename,'w') as outfile:
            json.dump(records, outfile)
        
    def sqliteOutput(self,args):
        self.conn = psycopg2.connect("dbname=postgres host=localhost user=admin")
        cur = self.conn.cursor()
        for r in args:
            cur.execute("insert into newsarticles(aid,title,summary,link,text,media,image,pid,category,pubdate) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",self.fix_format(r))
            self.conn.commit()

