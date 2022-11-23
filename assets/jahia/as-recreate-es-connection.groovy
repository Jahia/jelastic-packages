import org.jahia.services.content.JCRCallback
import org.jahia.services.content.JCRSessionWrapper
import org.jahia.services.content.JCRTemplate
import org.jahia.services.modulemanager.util.ModuleUtils
import org.jahia.utils.EncryptionUtils

import javax.jcr.RepositoryException

JCRCallback<Object> callback = new JCRCallback<Object>() {
    @Override
    Object doInJCR(JCRSessionWrapper session) throws RepositoryException {

        String SETTINGS_NODE_NAME = "/settings"
        String DBC_NODE_NAME = "databaseConnector"
        String DBC_NAME = "jahia-cloud_augmented-search"

        String ES_HOSTNAME = "PLACEHOLDER"
        String ES_PORT = "PLACEHOLDER"
        String ES_USER = "PLACEHOLDER"
        String ES_PASSWORD = "PLACEHOLDER"

        def settingsNode = session.getNode(SETTINGS_NODE_NAME)
        session.checkout(settingsNode);
        if (settingsNode.hasNode(DBC_NODE_NAME)) {
            dbConnectorNode = settingsNode.getNode(DBC_NODE_NAME)
            dbConnectorNode.remove()
        }
        def databaseConnectorNode = settingsNode.addNode(DBC_NODE_NAME, "dc:" + DBC_NODE_NAME)
        if (!databaseConnectorNode.hasNode(DBC_NAME)) {
            def elasticsearchConnection = databaseConnectorNode.addNode(DBC_NAME, "ec:elasticsearchConnection")
            elasticsearchConnection.setProperty("dc:id", DBC_NAME)
            elasticsearchConnection.setProperty("dc:databaseType", "ELASTICSEARCH")
            elasticsearchConnection.setProperty("dc:host", ES_HOSTNAME)
            elasticsearchConnection.setProperty("dc:port", ES_PORT)
            elasticsearchConnection.setProperty("dc:user", ES_USER)
            elasticsearchConnection.setProperty("dc:password", EncryptionUtils.passwordBaseEncrypt(ES_PASSWORD))
            elasticsearchConnection.setProperty("dc:isConnected", "true")
            elasticsearchConnection.setProperty("dc:options", "{\"useXPackSecurity\":true,\"useEncryption\":true}")
            session.save();
        }
        ModuleUtils.getModuleManager().stop("database-connector", null);
        ModuleUtils.getModuleManager().start("database-connector", null);
        return null

    }
}
JCRTemplate.instance.doExecuteWithSystemSession(callback);
