### Super User 
Login: root
- Password: ${settings.rootpwd}
- [${env.protocol}://${env.domain}/](${env.protocol}://${env.domain}/) 

### Manager User 
- Login: ${globals.mngr_user}
- Password: ${settings.toolspwd}
- [${env.protocol}://${env.domain}/tools/](${env.protocol}://${env.domain}/tools/) 

### DB User 
- Login: ${globals.db_user}
- Password ${globals.db_pass}
- [https://${nodes.sqldb.first.id}-${env.domain}/](https://node${nodes.sqldb.first.id}-${env.domain}/) 
