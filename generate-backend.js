// updates the generated typescript/angular client

// options
// delete the locally cached swagger-codegen-cli.jar when changing this URL
const swaggerVersion = "3.0.22";
const swaggerCodegenUrl =
  "https://repo1.maven.org/maven2/io/swagger/codegen/v3/swagger-codegen-cli/" +
  swaggerVersion +
  "/swagger-codegen-cli-" +
  swaggerVersion +
  ".jar";
const openApiBaseUrl = "http://localhost:8080/AristaFlowREST/";
const openApiAuth = null;

var execFile = require("child_process").execFile;
const { promisify } = require("util");
let download = require("download");
var execFile = promisify(execFile);
const fs = require("fs");
const { config } = require("process");
const replace = require("replace-in-file");

const swaggerCodegenJar = "swagger-codegen-cli.jar";
const swaggerFile = "swagger.json";
const configFile = "swagger-config.json";

// increment this whenever changing the generated output w/o updated major/minor versions of the endpoint
const genearteBackendVersion = 1;

// download the swagger code generator
function downloadSwagger() {
  const jarExists = fs.existsSync(swaggerCodegenJar);
  let jarPromise;
  if (!jarExists) {
    console.log("Downloading " + swaggerCodegenJar);
    jarPromise = download(swaggerCodegenUrl, "./", {
      filename: swaggerCodegenJar,
    }).then(() => {
      console.log(swaggerCodegenJar + " downloaded.");
    });
  } else {
    jarPromise = Promise.resolve();
    console.log(swaggerCodegenJar + " already downloaded");
  }
  return jarPromise;
}

function applySwaggerJsonFixes(swaggerJson) {
  var changed = false;

  // discriminator is only legal in conjunction with allOf, oneOf, anyOf
  var schemaWithMissingAllOf = [];
  for (var schemaName in swaggerJson.components.schemas) {
    var schema = swaggerJson.components.schemas[schemaName];
    if (schema.discriminator && !schema.allOf) {
      schemaWithMissingAllOf.push(schemaName);
    }
  }
  // schemaWithMissingAllOf = ["ActivityReference"];
  schemaWithMissingAllOf.forEach(function (schema) {
    changed = true;
    var old = swaggerJson.components.schemas[schema];
    var required;
    if (old.required) {
      required = old.required;
      delete old["required"];
    }
    var discriminator = old.discriminator;
    delete old["discriminator"];
    swaggerJson.components.schemas[schema] = {
      allOf: [{ $ref: "#/components/schemas/DummyParent" }, old],
      type: "object",
      discriminator: discriminator,
      required: required,
    };
    if (required) {
      swaggerJson.components.schemas[schema].required = required;
    }
  });

  if (changed) {
    swaggerJson.components.schemas.DummyParent = {
      type: "object",
    };
    console.log("Patched the following schemata: ", schemaWithMissingAllOf);
  }

  if (changed) {
    fs.writeFileSync(swaggerFile, JSON.stringify(swaggerJson));
  }
}

function applyPatches(generatedCodePath, project, serviceName) {
  // return;
  console.log("Patching generated code...");
  const options = {
    files: [generatedCodePath + project + "/**/*.py"],
    from: /replaced below/g,
    to: "replaced below",
  };
  let replaceResult = {};
  // Prevent any value for the "discriminator" property name specified by the subclass to be overwritten by the super class
  // replace:
  //         self.discriminator =
  // with
  //         if not(self.discriminator):
  //             self.discriminator =
  options.from = /        self\.discriminator =/g;
  options.to =
    '        if not(hasattr(self, "discriminator")) or not(self.discriminator):\n            self.discriminator =';
  replaceResult = replace.sync(options);
  // console.log("Patch result: ", replaceResult);

  // Use the attribute map to look up the value of the "discriminator" field in the response data
  // and use the value as is and not as "lower()"
  // replace:
  //         discriminator_value = data[self.discriminator].lower()
  // with:
  //         discriminator_value = data[self.attribute_map[self.discriminator]]
  options.from = /        discriminator_value = data\[self\.discriminator\]\.lower\(\)/g;
  options.to =
    "        discriminator_value = data[self.attribute_map[self.discriminator]]";
  replaceResult = replace.sync(options);

  options.from = /        return self\.discriminator_value_class_map\.get\(discriminator_value\)/g;
  options.to =
    "        return discriminator_value if not(self.__class__.__name__ == discriminator_value) else None";
  replaceResult = replace.sync(options);

  // console.log("Patch result: ", replaceResult);

  // Response code check: if the response code indicates an empty response (status code 204), return "None"
  // api_client.py: replace:
  //         # handle file downloading
  // with:
  //         if response.status == 204:
  //             return None
  //         # handle file downloading
  options.files = [generatedCodePath + project + "/api_client.py"];
  options.from = /        # handle file downloading/g;
  options.to =
    "        if response.status == 204:\n            return None\n        # handle file downloading";
  replaceResult = replace.sync(options);
  // console.log("Patch result: ", replaceResult);

  // package properties in setup.py
  options.files = [generatedCodePath + "/setup.py"];
  options.from = /    author_email="",/g;
  options.to =
    "    author=\"AristaFlow GmbH\",\n    author_email=\"info@aristaflow.com\",";
  replaceResult = replace.sync(options);
  // console.log("Patch result: ", replaceResult);
  options.from = /    description="AristaFlowREST\/[a-zA-Z]+",/g;
  options.to =
    '    description="AristaFlow BPM ' + serviceName + ' REST Client",';
  replaceResult = replace.sync(options);
  // console.log("Patch result: ", replaceResult);
  options.from = /    long_description="""\\.*"""/gms;
  options.to = '    long_description="AristaFlow BPM REST Client library for connecting to the ' + serviceName + ' endpoint. https://pypi.org/project/aristaflowpy/ provides APIs on top of the AristaFlow BPM REST endpoints for many use cases, so using aristaflowpy is recommended."';
  replaceResult = replace.sync(options);
  if (replaceResult.length != 1 || !replaceResult[0].hasChanged) {
    console.log(replaceResult);
    throw Error('Could not replace long_description');
  }

  console.log("Patching done");
}

function generateClient(service, project) {
  // remove any old swagger file
  if (fs.existsSync(swaggerFile)) {
    fs.unlinkSync(swaggerFile);
  }
  project = "af_" + project.replace(/-/g, "_");
  // download the current swagger file
  const options = { auth: openApiAuth, filename: swaggerFile };
  console.log("Downloading " + swaggerFile + " for service " + service);
  var dp;
  dp = download(
    openApiBaseUrl + service + "/openapi.json?apiLevel=full",
    "./",
    options
  ).then(() => {
    console.log(swaggerFile + " for service " + service + " downloaded");
  });
  return dp
    .then(() => {
      var generatedCodePath = "swagger/" + project + "/";
      if (fs.existsSync(generatedCodePath)) {
        console.log("Deleting old code from " + generatedCodePath);
        fs.rmdirSync(generatedCodePath, { recursive: true });
        if (fs.existsSync(generatedCodePath)) {
          console.log("Could not delete old code from " + generatedCodePath);
        }
      }
      var swaggerJson = JSON.parse(fs.readFileSync(swaggerFile));
      applySwaggerJsonFixes(swaggerJson);
      // update the package version: use the last place for the version of this generater script
      var packageVersion = swaggerJson.info.version;
      packageVersionParts = packageVersion.split('.');
      packageVersionParts[2] = genearteBackendVersion;
      packageVersion = packageVersionParts.join('.');
      fs.writeFileSync(
        configFile,
        JSON.stringify({
          projectName: project,
          packageName: project,
          packageVersion: packageVersion,
        })
      );
      console.log("Calling code generation for service " + service);
      return execFile(
        "java",
        [
          "-jar",
          swaggerCodegenJar,
          "generate",
          "--disable-examples",
          "-c",
          configFile,
          "-i",
          swaggerFile,
          "-o",
          generatedCodePath,
          "-l",
          "python",
        ],
        { maxBuffer: 1024 * 1024 }
      ).then((res) => {
        // clean up the swagger file
        if (fs.existsSync(swaggerFile)) {
          fs.unlinkSync(swaggerFile);
        }
        if (fs.existsSync(configFile)) {
          fs.unlinkSync(configFile);
        }

        console.log(
          "Code generation for service " + service + " completed, output:"
        );
        console.log(res.stdout);
        console.log(res.stderr);

        applyPatches(generatedCodePath, project, service);

        // copy the license file
        fs.copyFileSync('./LICENSE', generatedCodePath + 'LICENSE');

        console.log("Installing python module " + service);
        return execFile("python", ["setup.py", "install", "sdist", "bdist_wheel"], {
          cwd: "./swagger/" + project,
        }).then((res) => {
          console.log(
            "Installing python module " + service + "done, STDOUT/STDERR:"
          );
          console.log(res.stdout);
          console.log(res.stderr);
        });
      });
    })
    .catch((e) => {
      console.trace("Error caught");
      console.log(e);
    });
}

downloadSwagger()
  .then(() => {
    return generateClient(
      "OrgModelManager/OrgModelManager",
      "org-model-manager"
    );
  })
  .then(() => {
    return generateClient("LicenceManager/LicenceManager", "licence-manager");
  })
  .then(() => {
    return generateClient(
      "WorklistManager/WorklistManager",
      "worklist-manager"
    );
  })
  .then(() => {
    return generateClient(
      "ExecutionManager/ExecutionManager",
      "execution-manager"
    );
  })
  .then(() => {
    return generateClient("RuntimeService/RuntimeService", "runtime-service");
  })
  .then(() => {
    return generateClient("ProcessManager/ProcessManager", "process-manager");
  })
  .then(() => {
    return generateClient(
      "RuntimeManager/RemoteHTMLRuntimeManager",
      "remote-html-runtime-manager"
    );
  })
  .then(() => {
    return generateClient(
      "SimpleProcessImageRenderer/SimpleProcessImageRenderer",
      "simple-process-image-renderer"
    );
  })
  .then(() => {
    return generateClient(
      "ProcessImageRenderer/ProcessImageRenderer",
      "process-image-renderer"
    );
  })
  .then(() => {
    console.log(`
  Done
  `);
  });
