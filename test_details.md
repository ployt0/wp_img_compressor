# Test details

## Passwords:

- wordpress container root: password
- mysql root user on mariadb: mypass
- wordpressuser on mariadb: galoshes
- "Fred Test" admin user on WordPress: testtesttest
- Application Password on WordPress: IAU8 cEuo eAb9 BNMO bv3N T0jV

## WordPress heritage

Moore's law applies as well to storage and bandwidth as it does to today's
lithography advancements. I have unearthed articles advocating hosting images
separately from WordPress sites. These were published as late as the mid 2010s.

The advantages are obvious to anyone who wasn't born yesterday. The main
disadvantages are:

1. Lack of control of the images.
    - Sites close or monetise.
2. Search engines penalise this behaviour.
3. Some image hosting providers grow to dislike perceived commercialisation
   of their generosity.

With control comes responsibility; undoubtedly the second two points are
motivators to consider alternatives.

## Description of test VM

Install docker if needed:

```shell
sudo apt-get install docker.io
compgen -g | grep docker || sudo groupadd docker
sudo usermod -aG docker $USER
```

A logout is needed for the current user to pick up the permission.

Provision WordPress container with [`wp_provisioning.sh`](wp_provisioning.sh):

```shell
docker run -p 127.0.0.1:8080:80 -p 127.0.0.1:8066:22 --name mywp -d wordpress:6.0.1
#docker exec -it mywp /bin/bash
docker exec -i mywp bash < /home/vagrant/wp_provisioning.sh
```

`docker stop` or other halting activity, had a tendency to stop
ssh in the wordpress image, if so, try `/etc/init.d/ssh start`.

### An SSH target within our VM

We can now SSH from inside the VM:

```shell
ssh root@127.0.0.1 -p 8066
```

And cleanup:

```shell
docker rm mywp -f
```

### Choice of DB Image

`docker pull mariadb:10.8.3-jammy`

```shell
vagrant@vm4docker:~$ docker images
REPOSITORY   TAG             IMAGE ID       CREATED       SIZE
mysql        8.0.29-oracle   33037edcac9b   13 days ago   444MB
wordpress    6.0.1           826140609178   13 days ago   609MB
mysql        8.0.29-debian   0fc0e2322d42   2 weeks ago   528MB
mariadb      10.8.3-jammy    ea81af801379   7 weeks ago   383MB
```

I choose the smallest:

```shell
docker run --name mariadb -e MYSQL_ROOT_PASSWORD=mypass -p 3306:3306 -d mariadb:10.8.3-jammy
```

We need a small script, [wpdbsetup.sql](wpdbsetup.sql), to create the database
and user. We feed it into the container using exec:

```shell
docker exec -i mariadb mysql -uroot -pmypass < /home/vagrant/wpdbsetup.sql
```


### Christen the Web UI

We need to enter the [web UI](https://localhost:8542/wp-admin/install.php?step=1) to create the initial admin user:

> Fred Test
> testtesttest
> doesntmatter@notever.com

If instructions aren't followed very carefully it's not uncommon to see a
database connection error after this. `wp-config.php` is a good place to begin
the diagnosis.

Next we create an application password:

> testing_application
> IAU8 cEuo eAb9 BNMO bv3N T0jV

This didn't initially work, because [default permalinks do not use default
REST routing](https://developer.wordpress.org/rest-api/extending-the-rest-api/routes-and-endpoints/)

> On sites without pretty permalinks, the route is instead added to the URL as the rest_route parameter. For the above example, the full URL would then be http://example.com/?rest_route=/wp/v2/posts/123

The alternative would have been a big rewrite, ugly URLs, but potentially
greater compatibility. After I'd changed the permalinks, to anything other than
the default, plain, it worked.

### Towards automation

Now the database can be backed up to enable future test automation. Since this
is a one off we can `docker exec -ti mariadb bash` to enter a shell. Then:

```shell
# This greatly deflates storage requirements:
mysql -uroot -pmypass wordpress --execute="DELETE FROM wp_options WHERE option_name LIKE '%\_transient\_%'"
mysqldump -uroot -pmypass --single-transaction --flush-logs wordpress > $HOME/full_db_$(date +%y%m%d_%H%M).sql
```

and back out to:

```shell
docker cp mariadb:/root/full_db_220727_0953.sql /vagrant/
```

#### Restoration avoiding the UI

We need the wp-config.php just created (and copied), and the sql backup:

```shell
docker exec -i mariadb mysql -uroot -pmypass < /home/vagrant/wpdbsetup.sql
docker exec -i mariadb mysql -uroot -pmypass < /home/vagrant/full_db_220727_0953.sql
```

---

## Manual Test from host

If something is wrong I have collected the most useful commands here:

```shell
:~/PycharmProjects/wp_automations$ curl https://127.0.0.1:8542/wp-json/wp/v2/users/me -u "Fred Test:IAU8 cEuo eAb9 BNMO bv3N T0jV"
:~/PycharmProjects/wp_automations$ curl https://localhost:8382/wp-json/wp/v2/users/me -u "Fred Test:IAU8 cEuo eAb9 BNMO bv3N T0jV"
```

We must append `-k` or `--cacert self-signed-cacert.crt` to get the intended response:

```json
{
  "id": 1,
  "name": "Fred Test",
  "url": "https:\/\/localhost:8542",
  "description": "",
  "link": "https:\/\/localhost:8542\/author\/fred-test\/",
  "slug": "fred-test",
  "avatar_urls": {
    "24": "https:\/\/secure.gravatar.com\/avatar\/cd8042f93a1bf2bb38b77c5d3bde40b7?s=24&d=mm&r=g",
    "48": "https:\/\/secure.gravatar.com\/avatar\/cd8042f93a1bf2bb38b77c5d3bde40b7?s=48&d=mm&r=g",
    "96": "https:\/\/secure.gravatar.com\/avatar\/cd8042f93a1bf2bb38b77c5d3bde40b7?s=96&d=mm&r=g"
  },
  "meta": [],
  "_links": {
    "self": [
      {
        "href": "https:\/\/localhost:8542\/wp-json\/wp\/v2\/users\/1"
      }
    ],
    "collection": [
      {
        "href": "https:\/\/localhost:8542\/wp-json\/wp\/v2\/users"
      }
    ]
  }
}
```

If it doesn't work, check the equivalent from the VM and container:

```shell
docker exec -ti mywp bash
mysql -uwordpressuser232 -pgaloshes -h 172.17.0.3
select user_email, user_status, display_name from wp_users;
```

Unrelated to API, but still to WP functionality check the dev machine browser
loads https://localhost:8542/
